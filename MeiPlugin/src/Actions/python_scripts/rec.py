# rec.py — no mouse hooks; stop via deck double-tap or editor buttons
import os, sys, json, time, ctypes, threading, datetime, subprocess
from pathlib import Path

# ==== Find mp4 ====
def guess_capture_dirs():
    home = Path.home()
    candidates = [
        home / "Videos" / "Captures",
        home / "OneDrive" / "Videos" / "Captures",
        home / "OneDrive" / "影片" / "Captures",
        home / "影片" / "Captures",
    ]
    return [p for p in candidates if p.exists()]

def find_latest_mp4(dirs, within_seconds=600):
    latest = None
    latest_mtime = 0.0
    cutoff = time.time() - within_seconds
    for d in dirs:
        try:
            for p in d.glob("*.mp4"):
                try:
                    mt = p.stat().st_mtime
                    if mt >= cutoff and mt > latest_mtime:
                        latest = p; latest_mtime = mt
                except Exception:
                    pass
        except Exception:
            pass
    return latest

# ==== Paths ====
BASE = Path(os.environ.get(
    "MEI_LOG_DIR",
    r"C:\Users\seash\Documents\Loupedeck\MeiPlugin\ScreenRecordMarks"  # 你的預設
))
BASE.mkdir(parents=True, exist_ok=True)
DOCS    = BASE
STATE   = BASE / "session_state.json"
FLAG    = BASE / "stop.flag"
LOG_ERR = BASE / "daemon_error.txt"


# ==== Win+Alt+R (more compatible) ====
user32 = ctypes.windll.user32
MapVirtualKey = user32.MapVirtualKeyW
SendInput = user32.SendInput

KEYEVENTF_KEYUP    = 0x0002
KEYEVENTF_SCANCODE = 0x0008

VK_LWIN, VK_MENU, VK_R = 0x5B, 0x12, 0x52

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_uint),
                ("time", ctypes.c_uint),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint),
                ("U", INPUTUNION)]

def _send_scan(vk, up=False):
    scan = MapVirtualKey(vk, 0)
    ev = INPUT(); ev.type = 1
    ev.U.ki = KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0), 0, None)
    SendInput(1, ctypes.byref(ev), ctypes.sizeof(ev))

def _sleep(ms): time.sleep(ms / 1000.0)

def toggle_gamebar_record():
    """優先用 keyboard 套件送 'windows+alt+r'，失敗就回退 SendInput(scancode)。"""
    # A) keyboard 套件（簡單，但可能需要 admin，且命中率因環境而異）
    try:
        import keyboard
        # 先送 Win down，再送 Alt+R，最後 Win up，可降低吞鍵機率
        keyboard.press('windows')
        time.sleep(0.08)
        keyboard.send('alt+r')
        time.sleep(0.12)
        keyboard.release('windows')
        return
    except Exception:
        pass  # 沒裝、沒權限、或被擋都回退 B

    # B) 回退：ctypes SendInput（你原本/我幫你強化過的可靠路徑）
    try:
        # —— 全用 scancode，間隔拉長，避免被吞 —— 
        user32 = ctypes.windll.user32
        MapVirtualKey = user32.MapVirtualKeyW
        SendInput = user32.SendInput
        KEYEVENTF_KEYUP    = 0x0002
        KEYEVENTF_SCANCODE = 0x0008
        VK_LWIN, VK_MENU, VK_R = 0x5B, 0x12, 0x52

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                        ("dwFlags", ctypes.c_uint), ("time", ctypes.c_uint),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
        class INPUTUNION(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        class INPUT(ctypes.Structure):
            _fields_ = [("type", ctypes.c_uint), ("U", INPUTUNION)]

        def _scan(vk, up=False):
            scan = MapVirtualKey(vk, 0)
            ev = INPUT(); ev.type = 1
            ev.U.ki = KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0), 0, None)
            SendInput(1, ctypes.byref(ev), ctypes.sizeof(ev))

        def _sleep(ms): time.sleep(ms/1000.0)

        _scan(VK_LWIN, up=False); _sleep(120)
        _scan(VK_MENU, up=False); _sleep(120)
        _scan(VK_R,    up=False); _sleep(90)
        _scan(VK_R,    up=True);  _sleep(120)
        _scan(VK_MENU, up=True);  _sleep(120)
        _scan(VK_LWIN, up=True);  _sleep(120)
    except Exception:
        # 最後一層保底：什麼都做不到就算了（不要讓程式崩）
        pass


# ==== State helpers ====
def now_local(): return datetime.datetime.now()
def now_utc():   return datetime.datetime.utcnow()

def read_state():
    if not STATE.exists(): return None
    try: return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: return None

def write_state(d): STATE.write_text(json.dumps(d), encoding="utf-8")
def clear_state():
    try: STATE.unlink(missing_ok=True)
    except Exception: pass

def fmt_elapsed(start_utc_iso):
    start = datetime.datetime.fromisoformat(start_utc_iso)
    delta = now_utc() - start
    s = int(delta.total_seconds()); h, rem = divmod(s, 3600); m, s = divmod(rem, 60)
    return (f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"), delta

# ==== Tk editor dialog with Stop buttons ====
def mark_editor(prefix):
    """Return (note_text, action) where action in {'save','save_stop','stop','cancel'}"""
    import tkinter as tk
    from tkinter import ttk

    res = {"note": "", "action": "cancel"}

    root = tk.Tk()
    root.title("Mark editor"); root.attributes("-topmost", True)
    root.resizable(False, False)

    frm = ttk.Frame(root, padding=10); frm.grid(row=0, column=0)

    ttk.Label(frm, text="Describe this moment:").grid(row=0, column=0, sticky="w")
    txt = tk.Text(frm, width=48, height=4)
    txt.grid(row=1, column=0); txt.insert("1.0", prefix)

    btns = ttk.Frame(frm); btns.grid(row=2, column=0, pady=(8,0))
    def set_action(a):
        res["note"] = txt.get("1.0", "end-1c").strip()
        res["action"] = a
        root.destroy()

    ttk.Button(btns, text="Save", command=lambda: set_action("save")).grid(row=0, column=0, padx=4)
    ttk.Button(btns, text="Save & Stop", command=lambda: set_action("save_stop")).grid(row=0, column=1, padx=4)
    ttk.Button(btns, text="Stop (no mark)", command=lambda: set_action("stop")).grid(row=0, column=2, padx=4)
    ttk.Button(btns, text="Cancel", command=lambda: set_action("cancel")).grid(row=0, column=3, padx=4)

    root.bind("<Return>", lambda e: set_action("save"))
    root.bind("<Escape>", lambda e: set_action("cancel"))

    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w)//2; y = (root.winfo_screenheight() - h)//3
    root.geometry(f"+{x}+{y}")

    root.mainloop()
    return res["note"], res["action"]

# ==== Daemon: flag-only stop ====
def daemon_main(log_path: Path, start_utc_iso: str):
    def stop(reason="flag"):
        try: toggle_gamebar_record()
        except Exception: pass
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"# Recording session ended at {now_local():%Y-%m-%d %H:%M:%S.%f} ({reason})\n")
        except Exception: pass
        clear_state()
        os._exit(0)

    def watch_flag():
        while True:
            if FLAG.exists() or not STATE.exists():
                try: FLAG.unlink(missing_ok=True)
                except Exception: pass
                break
            time.sleep(0.25)
        stop("flag")

    threading.Thread(target=watch_flag, daemon=True).start()

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"# Recording session started at {now_local():%Y-%m-%d %H:%M:%S.%f}\n")
        f.write("# Each mark: [elapsed] | [local time] | note\n")

    while True:
        time.sleep(3600)

# ==== Commands ====
def cmd_start():
    session_id = now_local().strftime("%Y%m%d_%H%M%S")
    log_path   = DOCS / f"{session_id}_session.txt"
    start_iso  = now_utc().isoformat(timespec="seconds")
    write_state({"session_id": session_id, "log": str(log_path), "start_utc": start_iso})

    # 提示預期影片資料夾
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"# Likely video folder: {Path.home() / 'Videos' / 'Captures'}\n")
    except Exception:
        pass

    # 啟動監聽 daemon
    py = sys.executable
    DETACHED_PROCESS = 0x00000008
    subprocess.Popen([py, __file__, "_daemon", str(log_path), start_iso],
                     creationflags=DETACHED_PROCESS, close_fds=True)

    # 先喚起 Game Bar 視窗，再送 Win+Alt+R
    try:
        subprocess.Popen(["explorer.exe", "ms-gamebar:"], close_fds=True)
        time.sleep(0.8)              # 給它時間浮出
    except Exception:
        pass

    toggle_gamebar_record()          # 再送錄影切換

    print(str(log_path), flush=True)
    return 0


def cmd_daemon():
    if len(sys.argv) < 4: os._exit(1)
    log_path = Path(sys.argv[2]); start_iso = sys.argv[3]
    try:
        daemon_main(log_path, start_iso)
    except Exception as e:
        try:
            with open(LOG_ERR, "a", encoding="utf-8") as f:
                f.write(f"[{now_local()}] daemon crashed: {e}\n")
        except Exception: pass
        try: toggle_gamebar_record()
        except Exception: pass
        clear_state(); os._exit(1)

def _write_detected_video(log_path: Path, start_iso: str):
    """共用：在停止時寫入實際影片路徑"""
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            captures = Path.home() / "Videos" / "Captures"
            dirs = [captures] if captures.exists() else guess_capture_dirs()
            if dirs:
                f.write("# Probe capture dirs:\n")
                for d in dirs: f.write(f"#  - {d}\n")

            # 以 session 開始時間為下限（-60 秒緩衝）
            try:
                start_dt = datetime.datetime.fromisoformat(start_iso)
                start_cutoff = start_dt.timestamp() - 60
            except Exception:
                start_cutoff = 0.0

            latest = None
            latest_mtime = 0.0
            for d in dirs:
                for p in d.glob("*.mp4"):
                    try:
                        mt = p.stat().st_mtime
                        if mt >= start_cutoff and mt > latest_mtime:
                            latest = p; latest_mtime = mt
                    except Exception:
                        pass

            if latest:
                f.write(f"# Detected video: {latest}\n")
            else:
                f.write("# Detected video: <none found since session start>\n")
    except Exception:
        pass

def cmd_mark():
    st = read_state()
    if not st:
        print(f"No active session. DOCS={DOCS}", file=sys.stderr, flush=True)
        return 2

    start_iso = st["start_utc"]
    log_path  = Path(st["log"])
    elapsed_str, _ = fmt_elapsed(start_iso)

    note, action = mark_editor(f"{elapsed_str} — ")
    if action == "cancel":
        print("Canceled", flush=True)
        return 0

    # Save / Save & Stop → 先寫入標記
    if action in ("save", "save_stop"):
        line = f"{elapsed_str:<12} | {now_local():%H:%M:%S.%f}"[:-3] + f" | {note}"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line, flush=True)

    # Stop 分支（含 Save & Stop）
    if action in ("save_stop", "stop"):
        try: FLAG.touch()
        except Exception: pass
        try: toggle_gamebar_record()
        except Exception: pass
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"# Recording session ended at {now_local():%Y-%m-%d %H:%M:%S.%f} (editor)\n")
                f.write(f"# Capture folder: {Path.home() / 'Videos' / 'Captures'}\n")
        except Exception:
            pass
        _write_detected_video(log_path, start_iso)
        clear_state()
        print("__STOPPED__", flush=True)
        return 0

    return 0

def cmd_stop():
    st = read_state()
    log_path = Path(st["log"]) if st else (DOCS / "unknown_session.txt")
    start_iso = st["start_utc"] if st else now_utc().isoformat(timespec="seconds")

    try: FLAG.touch()
    except Exception: pass
    try: toggle_gamebar_record()
    except Exception: pass
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"# Recording session ended at {now_local():%Y-%m-%d %H:%M:%S.%f} (manual)\n")
    except Exception:
        pass
    _write_detected_video(log_path, start_iso)

    clear_state()
    print("Stopped", flush=True)
    return 0

def main():
    if len(sys.argv) < 2:
        print("usage: rec.py [start|mark|stop|_daemon]", file=sys.stderr); sys.exit(1)
    cmd = sys.argv[1].lower()
    if cmd == "start": sys.exit(cmd_start())
    if cmd == "mark":  sys.exit(cmd_mark())
    if cmd == "stop":  sys.exit(cmd_stop())
    if cmd == "_daemon": cmd_daemon(); sys.exit(0)
    sys.exit(1)

if __name__ == "__main__":
    main()
