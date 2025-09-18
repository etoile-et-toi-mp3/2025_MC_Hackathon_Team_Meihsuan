import sys
import platform
import pyautogui
import pywinctl as pwc
import pygetwindow as gw

def switch_and_paste(window_title):
    """
    Finds a window by its title, activates it, and then pastes from the clipboard.
    """
    try:
        # Find all windows that contain the given title
        windows = pwc.getWindowsWithTitle(window_title)

        # Iterate through the found windows
        for window in windows:
            print(f"Found window: {window.title}")
            window.activate()

        if not windows:
            print(f"Error: Window with title '{window_title}' not found.", file=sys.stderr)
            return

        # Wait a moment for the window to gain focus
        pyautogui.sleep(0.3)

        # --- 使用手動控制按鍵取代 hotkey ---
        modifier_key = 'command' if platform.system() == "Darwin" else 'ctrl'
        
        try:
            # 1. 按住修飾鍵 (Ctrl 或 Command)
            pyautogui.keyDown(modifier_key)
            # 2. 按下並放開 'v' 鍵
            pyautogui.press('v')
        finally:
            # 3. 放開修飾鍵
            pyautogui.keyUp(modifier_key)
        print(f"Successfully pasted into '{window_title}'")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)


if __name__ == "__main__":
    # The window title is passed as a command-line argument from C#
    if len(sys.argv) > 1:
        title_from_csharp = sys.argv[1]
        switch_and_paste(title_from_csharp)
    else:
        print("Error: No window title provided.", file=sys.stderr)