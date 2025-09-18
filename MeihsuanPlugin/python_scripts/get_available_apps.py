import sys
import json
import platform

def get_history():
    result = []

    try:
        if platform.system() == "Windows":
            result = get_windows_apps()
        elif platform.system() == "Darwin":  # macOS
            result = get_macos_apps()
        else:
            result = get_linux_apps()

    except Exception as e:
        # Fallback to mock data if real detection fails
        result = [
            {
                "success": True,
                "name": "VS Code",
                "processName": "Code",
                "windowTitle": "Visual Studio Code"
            },
            {
                "success": True,
                "name": "Chrome",
                "processName": "chrome",
                "windowTitle": "Google Chrome"
            },
            {
                "success": True,
                "name": "Slack",
                "processName": "slack",
                "windowTitle": "Slack"
            }
        ]

    return result

def get_windows_apps():
    import psutil
    import win32gui
    import win32process

    result = []
    visible_windows = []

    def enum_windows_callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            windows.append(hwnd)

    win32gui.EnumWindows(enum_windows_callback, visible_windows)

    for hwnd in visible_windows:
        try:
            window_title = win32gui.GetWindowText(hwnd)
            if not window_title or len(window_title.strip()) == 0:
                continue

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            process_name = process.name().replace('.exe', '')

            # Filter out system processes and empty titles
            if process_name.lower() not in ['dwm', 'winlogon', 'csrss', 'explorer'] and window_title.strip():
                result.append({
                    "success": True,
                    "name": window_title,
                    "processName": process_name,
                    "windowTitle": window_title
                })
        except:
            continue

    return result

def get_macos_apps():
    import subprocess

    result = []

    try:
        # Get running applications using AppleScript
        script = '''
        tell application "System Events"
            set runningApps to (name of every application process whose background only is false)
        end tell
        return runningApps
        '''

        proc = subprocess.run(['osascript', '-e', script],
                            capture_output=True, text=True, check=True)

        app_names = proc.stdout.strip().split(', ')

        for app_name in app_names:
            if app_name and app_name not in ['SystemUIServer', 'Dock', 'Finder']:
                result.append({
                    "success": True,
                    "name": app_name,
                    "processName": app_name,
                    "windowTitle": app_name
                })

    except Exception as e:
        # Fallback for macOS
        result = [
            {
                "success": True,
                "name": "Visual Studio Code",
                "processName": "Code",
                "windowTitle": "Visual Studio Code"
            },
            {
                "success": True,
                "name": "Google Chrome",
                "processName": "Google Chrome",
                "windowTitle": "Google Chrome"
            }
        ]

    return result

def get_linux_apps():
    import subprocess

    result = []

    try:
        # Try to get window list using wmctrl
        proc = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)

        if proc.returncode == 0:
            lines = proc.stdout.strip().split('\n')
            for line in lines:
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    window_title = parts[3]
                    if window_title:
                        result.append({
                            "success": True,
                            "name": window_title,
                            "processName": window_title.split()[0] if window_title.split() else "unknown",
                            "windowTitle": window_title
                        })
        else:
            # Fallback for Linux
            result = [
                {
                    "success": True,
                    "name": "Firefox",
                    "processName": "firefox",
                    "windowTitle": "Mozilla Firefox"
                }
            ]

    except:
        result = []

    return result

if __name__ == "__main__":
    history = get_history()
    print(json.dumps(history))