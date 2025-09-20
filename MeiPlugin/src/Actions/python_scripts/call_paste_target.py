# File: smart_paste_ui_v2.py

import sys
import platform
import pyautogui
import pywinctl as pwc
import customtkinter as ctk # 匯入 customtkinter 並簡稱為 ctk
import pygetwindow as gw
import time

# --- 核心貼上邏輯 (完全不變) ---
def switch_and_paste(window_title):
    try:
        windows = pwc.getWindowsWithTitle(window_title)
        if not windows:
            print(f"Error: Window with title '{window_title}' not found.", file=sys.stderr)
            return

        window = windows[0]
        window.activate()
        pyautogui.sleep(0.3)
                # 在 activate() 後加入這段
        win_box = window.box  # x, y, width, height
        click_x = win_box.left + win_box.width // 2
        click_y = win_box.top + int(win_box.height * 0.85)  # 下半部

        pyautogui.click(click_x, click_y)
        pyautogui.sleep(0.2)


        modifier_key = 'command' if platform.system() == "Darwin" else 'ctrl'
        try:
            pyautogui.keyDown(modifier_key)
            pyautogui.press('v')
        finally:
            pyautogui.keyUp(modifier_key)
        print(f"Successfully pasted into '{window_title}'")
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)

# --- 全新的 UI 建立函式 ---
def create_modern_selection_ui(window_titles):
    # 設定外觀模式 (System, Dark, Light)
    ctk.set_appearance_mode("Dark")
    # 設定預設主題顏色
    ctk.set_default_color_theme("blue")

    # 主視窗從 tk.Tk() 變成 ctk.CTk()
    app = ctk.CTk()
    app.title("Smart Paste")
    
    # --- 按鈕點擊事件 ---
    def on_paste_click(selected_title):
        # 點擊按鈕後，先關閉 UI，再執行貼上
        app.destroy() 
        switch_and_paste(selected_title)

    # 建立一個可以滾動的框架 (Frame) 來容納所有按鈕
    scrollable_frame = ctk.CTkScrollableFrame(app, label_text="Select an app to paste into", width=1000, height=1000)
    scrollable_frame.pack(pady=20, padx=20, fill="both", expand=True)

    # --- 為每個視窗標題建立一個獨立的按鈕 ---
    for title in window_titles:
        button = ctk.CTkButton(scrollable_frame, text=title, command=lambda t=title: on_paste_click(t))
        # 使用 pack 將按鈕一個個加到滾動框架中
        button.pack(pady=4, padx=10, fill="x")
    print("create button")

    # --- 視窗行為 ---
    app.update_idletasks()
    width = app.winfo_width()
    height = app.winfo_height()
    screen_width = app.winfo_screenwidth()
    screen_height = app.winfo_screenheight()

    # 計算螢幕正中央的 x 和 y 座標
    final_x = (screen_width // 2) - (width // 2)
    final_y = (screen_height // 2) - (height // 2)

    app.geometry("500x500")
    app.attributes('-topmost', True) # 保持在最上層
    app.mainloop()

# --- 腳本進入點 (幾乎不變) ---
if __name__ == "__main__":
    try:
        # titles = pwc.getAllTitles()
        titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
        print(titles)

        
        if titles:
            create_modern_selection_ui(titles)
        else:
            # 即使出錯，也用 ctk 來顯示訊息
            ctk.set_appearance_mode("Dark")
            app = ctk.CTk()
            app.withdraw() # 隱藏主視窗
            # customtkinter 沒有 messagebox，但可以用一個簡單的 Toplevel 視窗來模擬
            dialog = ctk.CTkToplevel(app)
            dialog.title("Info")
            label = ctk.CTkLabel(dialog, text="No active application windows were found.")
            label.pack(padx=20, pady=20)
            dialog.attributes('-topmost', True)
            dialog.after(2000, dialog.destroy) # 2秒後自動關閉
            dialog.mainloop()
            
    except Exception as e:
        print(f"A critical error occurred: {e}", file=sys.stderr)