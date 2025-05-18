import psutil, time, os, curses
from datetime import datetime, timedelta

# Konfiguration
UPDATE_INTERVAL = 2
BAR_WIDTH = 50
BAR_FILL = "#"
BAR_EMPTY = "-"
BORDER_VERTICAL = "|"
BORDER_HORIZONTAL = "-" 
BORDER_CORNER = "+"

# Schwellenwerte
CPU_WARNING = 50
CPU_CRITICAL = 75
TEMP_WARNING = 70
TEMP_CRITICAL = 85
RAM_WARNING = 75
RAM_CRITICAL = 90

def init_colors():
    """Initialisiert die Farbpaare"""
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Normal
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Warnung
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)    # Kritisch
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Überschriften
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Highlights
    curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)   # Details
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Rahmen

def get_size(bytes):
    """Konvertiert Bytes in lesbare Größen mit schöner Formatierung"""
    for unit in ['', 'K', 'M', 'G', 'T', 'P']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}B"
        bytes /= 1024
    return f"{bytes:.2f} PB"

def get_cpu_bar(win, percent, y, x, width=BAR_WIDTH):
    """Zeichnet eine verbesserte CPU-Auslastungsleiste mit Farbverlauf"""
    filled = int(width * percent / 100)
    
    if percent < CPU_WARNING:
        color = curses.color_pair(1)
    elif percent < CPU_CRITICAL:
        color = curses.color_pair(2)
    else:
        color = curses.color_pair(3)
        
    win.addstr(y, x, BORDER_VERTICAL + 
               BAR_FILL * filled + BAR_EMPTY * (width - filled) + 
               BORDER_VERTICAL, color)

def get_system_info():
    """Sammelt erweiterte System Informationen"""
    cpu_info = {
        'auslastung': psutil.cpu_percent(interval=1),
        'frequenz': psutil.cpu_freq()[0] if psutil.cpu_freq() else 0,
        'cores': psutil.cpu_percent(percpu=True),
        'temp': psutil.sensors_temperatures().get('coretemp', [])[0].current if hasattr(psutil, 'sensors_temperatures') and psutil.sensors_temperatures().get('coretemp') else 0
    }
    
    ram = psutil.virtual_memory()
    ram_info = {
        'gesamt': get_size(ram.total),
        'verfuegbar': get_size(ram.available),
        'verwendet': get_size(ram.used),
        'auslastung': ram.percent,
        'cached': get_size(ram.cached)
    }
    
    swap = psutil.swap_memory()
    swap_info = {
        'gesamt': get_size(swap.total),
        'verwendet': get_size(swap.used),
        'auslastung': swap.percent
    }

    # Netzwerkstatistik
    net = psutil.net_io_counters()
    net_info = {
        'bytes_sent': get_size(net.bytes_sent),
        'bytes_recv': get_size(net.bytes_recv)
    }

    # Systemlaufzeit
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    uptime_info = str(timedelta(seconds=int(uptime.total_seconds())))
    
    try:
        processes = sorted(
            [{'pid': p.info['pid'], 
              'name': p.info['name'], 
              'cpu': p.info['cpu_percent'],
              'speicher': p.info['memory_percent'],
              'status': p.info['status'],
              'erstellt': datetime.fromtimestamp(p.create_time()).strftime('%H:%M:%S')}
             for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time'])
             if all(key in p.info for key in ['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time'])],
            key=lambda x: x['cpu'], reverse=True
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        processes = []
    
    return cpu_info, ram_info, swap_info, processes, net_info, uptime_info

def display_info(stdscr):
    """Zeigt System Informationen in einem verbesserten htop-Stil an"""
    init_colors()
    curses.curs_set(0)
    stdscr.nodelay(1)
    
    while True:
        try:
            cpu_info, ram_info, swap_info, processes, net_info, uptime_info = get_system_info()
            max_y, max_x = stdscr.getmaxyx()
            stdscr.clear()

            # Schönerer Rahmen für das gesamte Interface
            stdscr.attron(curses.color_pair(7))
            stdscr.border(
                BORDER_VERTICAL,
                BORDER_VERTICAL,
                BORDER_HORIZONTAL,
                BORDER_HORIZONTAL,
                BORDER_CORNER,
                BORDER_CORNER,
                BORDER_CORNER,
                BORDER_CORNER
            )
            stdscr.attroff(curses.color_pair(7))

            # Verbesserter Titel mit doppeltem Rahmen
            title = "System Monitoring"
            box_width = len(title) + 4
            center_x = (max_x - box_width) // 2
            stdscr.addstr(0, center_x, BORDER_CORNER + 
                         BORDER_HORIZONTAL * (box_width-2) + 
                         BORDER_CORNER, 
                         curses.color_pair(4) | curses.A_BOLD)
            stdscr.addstr(1, center_x, "| " + title + " |", curses.color_pair(4) | curses.A_BOLD)
            stdscr.addstr(2, center_x, BORDER_CORNER + 
                         BORDER_HORIZONTAL * (box_width-2) + 
                         BORDER_CORNER, 
                         curses.color_pair(4) | curses.A_BOLD)
            
            current_y = 4

            # Systemlaufzeit anzeigen
            stdscr.addstr(current_y, 2, f"+--- Systemlaufzeit: {uptime_info} " + "-" * (max_x - 25 - len(uptime_info)) + "+",
                        curses.color_pair(5) | curses.A_BOLD)
            current_y += 2
            
            # CPU Informationen
            stdscr.addstr(current_y, 2, "+--- CPU Auslastung " + "-" * (max_x - 25) + "+", 
                        curses.color_pair(5) | curses.A_BOLD)
            for i, core in enumerate(cpu_info['cores']):
                if current_y + 1 + i < max_y - 1:
                    stdscr.addstr(current_y + 1 + i, 4, f"| Core {i}: {core:>5.1f}% ", 
                                curses.color_pair(6))
                    get_cpu_bar(stdscr, core, current_y + 1 + i, 20)
                    stdscr.addstr(current_y + 1 + i, max_x - 3, "|", curses.color_pair(6))
            
            current_y += len(cpu_info['cores']) + 1
            
            if cpu_info['temp'] and current_y < max_y - 1:
                temp_color = curses.color_pair(2 if cpu_info['temp'] < TEMP_WARNING 
                                             else 3)
                stdscr.addstr(current_y, 4, f"| Temperatur: {cpu_info['temp']}°C", temp_color)
                stdscr.addstr(current_y, max_x - 3, "|", curses.color_pair(6))
                current_y += 1
                stdscr.addstr(current_y, 2, "+" + "-" * (max_x - 4) + "+", curses.color_pair(5))
                current_y += 1

            # Netzwerkaktivität
            if current_y < max_y - 3:
                stdscr.addstr(current_y, 2, "+--- Netzwerk " + "-" * (max_x - 18) + "+",
                            curses.color_pair(5) | curses.A_BOLD)
                stdscr.addstr(current_y + 1, 4, f"| Upload: {net_info['bytes_sent']} | Download: {net_info['bytes_recv']}", 
                            curses.color_pair(6))
                stdscr.addstr(current_y + 2, 2, "+" + "-" * (max_x - 4) + "+", curses.color_pair(5))
                current_y += 3

            # RAM Informationen
            if current_y < max_y - 4:
                stdscr.addstr(current_y, 2, "+--- Arbeitsspeicher " + "-" * (max_x - 25) + "+", 
                            curses.color_pair(5) | curses.A_BOLD)
                stdscr.addstr(current_y + 1, 4, 
                            f"| Verwendet: {ram_info['verwendet']} von {ram_info['gesamt']} ({ram_info['auslastung']}%)")
                get_cpu_bar(stdscr, ram_info['auslastung'], current_y + 1, 50)
                stdscr.addstr(current_y + 2, 4, f"| Cache: {ram_info['cached']}", curses.color_pair(6))
                stdscr.addstr(current_y + 3, 2, "+" + "-" * (max_x - 4) + "+", curses.color_pair(5))
                current_y += 4

            # Swap Informationen
            if current_y < max_y - 3:
                stdscr.addstr(current_y, 2, "+--- Swap " + "-" * (max_x - 15) + "+", 
                            curses.color_pair(5) | curses.A_BOLD)
                stdscr.addstr(current_y + 1, 4, 
                            f"| Verwendet: {swap_info['verwendet']} von {swap_info['gesamt']} ({swap_info['auslastung']}%)")
                get_cpu_bar(stdscr, swap_info['auslastung'], current_y + 1, 50)
                stdscr.addstr(current_y + 2, 2, "+" + "-" * (max_x - 4) + "+", curses.color_pair(5))
                current_y += 3

            # Prozess Liste
            if current_y < max_y - 3:
                stdscr.addstr(current_y, 2, "+--- Prozesse " + "-" * (max_x - 18) + "+", 
                            curses.color_pair(5) | curses.A_BOLD)
                header = "| PID    CPU%   MEM%   STATUS  ZEIT     NAME"
                stdscr.addstr(current_y + 1, 2, header, curses.color_pair(4))
                stdscr.addstr(current_y + 1, max_x - 3, "|", curses.color_pair(4))
                
                for i, proc in enumerate(processes[:max_y - current_y - 4]):
                    if current_y + 2 + i < max_y - 2:
                        color = curses.color_pair(1) if proc['cpu'] < CPU_WARNING else \
                                curses.color_pair(2) if proc['cpu'] < CPU_CRITICAL else \
                                curses.color_pair(3)
                        stdscr.addstr(current_y + 2 + i, 2, "|", color)
                        stdscr.addstr(current_y + 2 + i, 4, 
                            f"{proc['pid']:<6} {proc['cpu']:>5.1f} {proc['speicher']:>6.1f} {proc['status']:<7} {proc['erstellt']} {proc['name'][:max_x-45]}", 
                            color)
                        stdscr.addstr(current_y + 2 + i, max_x - 3, "|", color)
                
                stdscr.addstr(min(current_y + 2 + len(processes), max_y - 2), 2, 
                             "+" + "-" * (max_x - 4) + "+", curses.color_pair(5))

            # Statuszeile
            status = f"'q' zum Beenden | Aktualisierung alle {UPDATE_INTERVAL} Sekunden"
            stdscr.addstr(max_y-1, (max_x - len(status)) // 2, status, curses.color_pair(4) | curses.A_DIM)
            stdscr.refresh()
            
            key = stdscr.getch()
            if key == ord('q'):
                break
                
            time.sleep(UPDATE_INTERVAL)
            
        except curses.error:
            continue

def main():
    try:
        curses.wrapper(display_info)
    except KeyboardInterrupt:
        print("\nProgramm beendet.")
    except Exception as e:
        print(f"\nEin Fehler ist aufgetreten: {str(e)}")

if __name__ == "__main__":
    main()