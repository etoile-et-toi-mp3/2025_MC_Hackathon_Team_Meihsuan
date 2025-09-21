# rec.py — lean & fast: keyboard first, SendInput fallback; no mouse hooks
import os, sys, json, time, ctypes, threading, datetime, subprocess
from pathlib import Path

# ---------------- Config ----------------
# 快速模式延遲（秒）：盡量短、但仍保留最低穩定度
T_WIN_DN   = 0.04
T_ALT_SEQ  = 0.04
T_WIN_UP   = 0.04
T_FALLBACK = 0.08  # SendInput fallback 單步延遲

# ---------------- Paths -----------------
BASE = Path(os.environ.get(
    "FloWork_LOG_DIR",
    r"C:\Users\miche\Documents\Loupedeck\FloWorkPlugin\ScreenRecordMarks"
))
BASE.mkdir(parents=True, exist_ok=True)
DOCS    = BASE
STATE   = BASE / "session_state.json"
FLAG    = BASE / "stop.flag"
LOG_ERR = BASE / "daemon_error.txt"

# ---------------- SendInput (一次定義) ---
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

def _scan_key(vk, up=False):
    sc = MapVirtualKey(vk, 0)
    ev = INPUT(); ev.type = 1
    ev.U.ki = KEYBDINPUT(0, sc, KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0), 0, None)
    SendInput(1, ctypes.byref(ev), ctypes.sizeof(ev))

# ---------------- Captures scan ----------
def _captures_dirs():
    # 先用你已確認的預設，其次常見候選
    home = Path.home()
    preferred = home / "Videos" / "Captures"
    if preferred.exists():
        return [preferred]
    cands = [
        home / "OneDrive" / "Videos" / "Captures",
        home / "OneDrive" / "影片" / "Captures",
        home / "影片" / "Captures",
    ]
    return [p for p in cands if p.exists()]

def _write_detected_video(log_path: Path, start_iso: str):
    """停止時寫入實際影片路徑（只掃一次、從最近檔開始）"""
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            dirs = _captures_dirs()
            if dirs:
                f.write("# Probe capture dirs:\n")
                for d in dirs: f.write(f"#  - {d}\n")
            try:
                start_dt = datetime.datetime.fromisoformat(start_iso)
                start_cutoff = start_dt.timestamp() - 60
            except Exception:
                start_cutoff = 0.0

            latest = None
            latest_mtime = -1.0
            for d in dirs:
                # 直接按修改時間倒序遍歷（效率較好）
                try:
                    files = sorted(d.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
                except Exception:
                    files = list(d.glob("*.mp4"))
                for p in files:
                    try:
                        mt = p.stat().st_mtime
                        if mt >= start_cutoff:
                            latest = p; latest_mtime = mt
                            break
                    except Exception:
                        pass
                if latest: break

            if latest:
                f.write(f"# Detected video: {latest}\n")
            else:
                f.write("# Detected video: <none found since session start>\n")
    except Exception:
        pass

# ---------------- Desktop note file helpers ----------------
def _desktop_dir():
    up = os.environ.get("USERPROFILE") or str(Path.home())
    d = Path(up) / "Desktop"
    return d if d.exists() else Path.home() / "Desktop"
    # return Path(r"C:\Users\seash\Videos\Captures")

# def _desktop_note_path(session_id: str) -> Path:
#     dirs = _captures_dirs()
#     # 每個 session 一個獨立檔，避免覆蓋
#     return dirs[0] / f"MeiRecord_Notes_{session_id}.txt"

def _desktop_note_path(session_id: str) -> Path:
    base = Path(r"C:\Users\miche\Videos\Captures")
    notes_dir = base / "FloworkNotes"        # 新增的子資料夾
    try:
        notes_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return notes_dir / f"FloWorkRecord_Notes_{session_id}.txt"

def _init_desktop_note(session_id: str):
    """建立/覆寫桌面筆記檔，寫入標頭"""
    p = _desktop_note_path(session_id)
    try:
        p.write_text("mark: [elapsed] — note\n", encoding="utf-8")
    except Exception:
        pass

def _append_desktop_note(session_id: str, elapsed_str: str, note_text: str):
    """
    將一條筆記追加到桌面檔。
    若 note 本身已是 'MM:SS — ...' 或 'HH:MM:SS — ...' 形態，直接用；
    否則用 elapsed 補齊成 'MM:SS — note'。
    """
    p = _desktop_note_path(session_id)
    try:
        line = note_text.strip()
        # 符合 'MM:SS — ...' 或 'HH:MM:SS — ...' 就直接用
        import re
        if not re.match(r"^\d{2}:\d{2}(:\d{2})?\s+—\s+.+", line):
            line = f"{elapsed_str} — {line}"
        with open(p, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ---------------- Window & file-based recording detection (STRICT) ----------------
import ctypes.wintypes as wt

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId

# 取 exe 路徑（可能需要權限；失敗時回空字串）
psapi = ctypes.windll.psapi
kernel32 = ctypes.windll.kernel32
OpenProcess = kernel32.OpenProcess
CloseHandle = kernel32.CloseHandle
GetModuleFileNameExW = psapi.GetModuleFileNameExW
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010

def _get_title(hwnd):
    if not IsWindowVisible(hwnd): return ""
    n = GetWindowTextLengthW(hwnd)
    if n <= 0: return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    GetWindowTextW(hwnd, buf, len(buf))
    return buf.value

def _get_pid(hwnd):
    pid = wt.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

def _get_exe_path(pid):
    h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h: return ""
    try:
        buf = ctypes.create_unicode_buffer(512)
        if GetModuleFileNameExW(h, None, buf, len(buf)) > 0:
            return buf.value
        return ""
    finally:
        CloseHandle(h)

_RECORDING_TITLE_HINTS = ("Recording","Capturing","Capture","錄製","錄影","擷取","正在錄製","錄製中","录制")
_GAMEBAR_EXE_HINTS = ("gamebar","xboxgamebar")  # exe 名稱關鍵字

def _gamebar_recording_ui_visible():
    """標題含錄影關鍵字 + 所屬進程 exe 包含 GameBar 才算錄影 UI 可見。"""
    hit = False
    def _cb(hwnd, _):
        nonlocal hit
        if hit: return False
        t = _get_title(hwnd)
        if not t or not any(k in t for k in _RECORDING_TITLE_HINTS):
            return True
        exe = _get_exe_path(_get_pid(hwnd)).lower()
        if any(h in exe for h in _GAMEBAR_EXE_HINTS) or exe.endswith(r"\xboxgamebar.exe"):
            hit = True
            return False
        return True
    EnumWindows(EnumWindowsProc(_cb), 0)
    return hit

def _latest_mp4_under_captures():
    dirs = _captures_dirs()
    for d in dirs:
        try:
            files = sorted(d.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if files: return files[0]
        except Exception: pass
    return None

def is_recording_active_once(prev_path=None, prev_size=None, growth_required=True, debug_log=None):
    """
    daemon 輪詢用：回傳 (active:bool, curr_path:Path|None, curr_size:int)
    UI 命中 -> True；否則看 mp4 是否「相對上一輪」變大（warmup 可放寬一次）。
    """
    if _gamebar_recording_ui_visible():
        mp4 = _latest_mp4_under_captures()
        size = -1
        try: size = mp4.stat().st_size if mp4 else -1
        except Exception: pass
        return True, mp4, size

    mp4 = _latest_mp4_under_captures()
    size = -1
    try: size = mp4.stat().st_size if mp4 else -1
    except Exception: pass

    if mp4 and size >= 0:
        if not growth_required:
            return True, mp4, size  # warmup 放寬
        if prev_path is not None and prev_path == mp4 and prev_size is not None and size > prev_size:
            return True, mp4, size

    return False, mp4, size

def wait_recording_active(timeout=3.5, poll=0.1):
    """起錄確認：UI 命中或 mp4 有成長即 True；否則 False（不阻塞整體流程）。"""
    t0 = time.time()
    last_path, last_size = None, None
    warmup = True
    while time.time() - t0 < timeout:
        active, curr_path, curr_size = is_recording_active_once(
            prev_path=last_path, prev_size=last_size, growth_required=not warmup
        )
        if curr_path is not None:
            last_path, last_size = curr_path, curr_size
        if warmup: warmup = False
        if active: return True
        time.sleep(poll)
    return False

# ---------------- Hotkey: Win+Alt+R -----
def toggle_gamebar_record():
    """最快路徑：keyboard；失敗才用 SendInput(scancode)。"""
    # A) keyboard（這台機器最穩，也最快）
    try:
        import keyboard
        keyboard.press('windows'); time.sleep(T_WIN_DN) # 0.04
        keyboard.send('alt+r');    time.sleep(T_ALT_SEQ) # 0.06
        keyboard.release('windows'); time.sleep(T_WIN_UP) # 0.04
        return
    except Exception:
        pass
    # # B) fallback：SendInput（短延遲）
    # _scan_key(VK_LWIN, False); time.sleep(T_FALLBACK)
    # _scan_key(VK_MENU, False); time.sleep(T_FALLBACK)
    # _scan_key(VK_R,    False); time.sleep(T_FALLBACK * 0.8)
    # _scan_key(VK_R,    True ); time.sleep(T_FALLBACK)
    # _scan_key(VK_MENU, True ); time.sleep(T_FALLBACK)
    # _scan_key(VK_LWIN, True ); time.sleep(T_FALLBACK)

# ---------------- State helpers ----------
now_local = lambda: datetime.datetime.now()
now_utc   = lambda: datetime.datetime.utcnow()

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



# ---------------- Tk note editor ----------
def mark_editor(prefix):
    """Return (note_text, action) where action in {'save','save_stop','stop','cancel'}"""
    import tkinter as tk
    from tkinter import ttk

    # ----- palette（深色極簡風） -----
    BG     = "#1e1f22"  # 視窗背景
    PANEL  = "#2b2d31"  # 卡片/輸入區
    FG     = "#e6e6e6"  # 一般文字
    MUTED  = "#b7bbc3"  # 次要文字
    LINE   = "#3b3d42"  # 細線/邊框
    ACCENT = "#3b82f6"  # 強調色（藍）
    ACCENT_HOVER = "#2563eb"

    res = {"note": "", "action": "cancel"}

    root = tk.Tk()
    root.title("Mark editor")
    root.configure(bg=BG)
    root.attributes("-topmost", True)
    root.resizable(False, False)

    # ---- ttk theme & styles ----
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # 背景顏色要套到各元件
    style.configure("Editor.TFrame", background=BG)
    style.configure("Card.TFrame", background=PANEL, borderwidth=1, relief="solid")
    style.map("Card.TFrame", background=[("active", PANEL)])

    style.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI", 12, "bold"))
    style.configure("Hint.TLabel",  background=BG, foreground=MUTED, font=("Segoe UI", 9))

    # 按鈕：極簡扁平＋hover/press
    style.configure("Editor.TButton",
                    background=LINE, foreground=FG, borderwidth=0,
                    padding=(12, 8), font=("Segoe UI", 10))
    style.map("Editor.TButton",
              background=[("active", ACCENT_HOVER), ("pressed", ACCENT), ("!active", LINE)],
              foreground=[("disabled", "#777777"), ("!disabled", FG)])

    # ---- layout: 外層留空氣感的邊距 ----
    outer = ttk.Frame(root, style="Editor.TFrame", padding=16)
    outer.grid(row=0, column=0, sticky="nsew")

    # 標題與輕提示
    ttk.Label(outer, text="Describe this moment", style="Title.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(outer, text="Keep it short and meaningful.", style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(2,10))

    # 卡片式輸入區（細邊線＋內距）
    card = ttk.Frame(outer, style="Card.TFrame", padding=10)
    card.grid(row=2, column=0, sticky="ew")
    outer.columnconfigure(0, weight=1)

    # 純 tk.Text 也套深色
    txt = tk.Text(card,
                  width=52, height=5,
                  wrap="word",
                  bg=PANEL, fg=FG,
                  insertbackground=FG,     # 游標顏色
                  selectbackground="#3d5a99",
                  relief="flat",
                  padx=8, pady=6)
    txt.grid(row=0, column=0, sticky="ew")
    txt.insert("1.0", prefix)
    txt.focus_set()

    # 底部按鈕列（右對齊）
    btns = ttk.Frame(outer, style="Editor.TFrame")
    btns.grid(row=3, column=0, pady=(12, 0), sticky="e")

    def set_action(a):
        res["note"] = txt.get("1.0", "end-1c").strip()
        res["action"] = a
        root.destroy()

    ttk.Button(btns, text="Save",            style="Editor.TButton",
               command=lambda: set_action("save")).grid(row=0, column=0, padx=(0,8))
    ttk.Button(btns, text="Save & Stop",     style="Editor.TButton",
               command=lambda: set_action("save_stop")).grid(row=0, column=1, padx=(0,8))
    ttk.Button(btns, text="Stop (no mark)",  style="Editor.TButton",
               command=lambda: set_action("stop")).grid(row=0, column=2, padx=(0,8))
    ttk.Button(btns, text="Cancel",          style="Editor.TButton",
               command=lambda: set_action("cancel")).grid(row=0, column=3)

    # 熱鍵（保持你的原行為）
    root.bind("<Return>", lambda e: set_action("save"))
    root.bind("<Escape>", lambda e: set_action("cancel"))

    # ---- window chrome: 置中、細邊框感 ----
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w)//2
    y = (root.winfo_screenheight() - h)//3
    root.geometry(f"+{x}+{y}")

    # 額外：把整體邊界用一層實心 Frame 做微弱描邊效果（可選）
    root.configure(highlightthickness=1, highlightbackground=LINE)

    root.mainloop()
    return res["note"], res["action"]



# ---------------- Daemon (flag-only) -----
def daemon_main(log_path: Path, start_utc_iso: str):
    # ---- 可調參數 ----
    POLL = 0.5              # 輪詢間隔
    GRACE = 2.0             # 非錄影累積到多少秒才判停
    FILE_SWITCH_GRACE = 2.0 # 產生新 mp4 後的保護期（視為仍在錄影）
    MIN_RUNTIME_GUARD = 3.0 # 起錄後最短不自動停止秒數（防誤判）

    def logline(msg):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    def stop(reason="flag", send_hotkey=True):
        if send_hotkey:
            try: toggle_gamebar_record()
            except Exception: pass
        logline(f"# Recording session ended at {now_local():%Y-%m-%d %H:%M:%S.%f} ({reason})")
        _write_detected_video(log_path, start_utc_iso)
        clear_state()
        os._exit(0)

    # 只監看 FLAG，避免 STATE 短暫不可見就誤停
    def watch_flag():
        interval = 0.25
        while True:
            if FLAG.exists():
                try: FLAG.unlink(missing_ok=True)
                except Exception: pass
                break
            time.sleep(interval)
        stop("flag", send_hotkey=False)

    threading.Thread(target=watch_flag, daemon=True).start()

    logline(f"# Recording session started at {now_local():%Y-%m-%d %H:%M:%S.%f}")
    logline("# Each mark: [elapsed] | [local time] | note")

    # ---- 狀態變數 ----
    not_active_for = 0.0
    no_growth_for  = 0.0
    prev_path, prev_size = None, None
    first_loops = 10
    last_switch_until = 0.0
    start_epoch = time.time()

    while True:
        try:
            now = time.time()
            growth_required = (first_loops <= 0)

            active, curr_path, curr_size = is_recording_active_once(
                prev_path, prev_size, growth_required=growth_required
            )

            # 檔案切換偵測（新 mp4 產生）
            path_switched = (prev_path is not None and curr_path is not None and prev_path != curr_path)

            if path_switched:
                # 新檔保護：視為仍在錄影，計數器歸零，開啟保護期
                last_switch_until = now + FILE_SWITCH_GRACE
                no_growth_for = 0.0
                not_active_for = 0.0
                active = True
            else:
                # 切換保護期間一樣強制視為活躍
                if now < last_switch_until:
                    active = True

            # 檔案成長統計（僅同一檔時累積）
            if (not path_switched) and prev_path and curr_path and prev_path == curr_path \
               and prev_size is not None and curr_size is not None:
                if curr_size > prev_size:
                    no_growth_for = 0.0
                else:
                    no_growth_for += POLL

            # 活躍/非活躍累積
            if active:
                not_active_for = 0.0
            else:
                not_active_for += POLL

            if first_loops > 0:
                first_loops -= 1

            # （可關的除錯）——穩定後可註解
            
            # cp = str(curr_path) if curr_path else "<none>"
            # logline(f"[det] active={active} file={cp} size={curr_size} "
            #         f"no_growth_for={no_growth_for:.1f}s not_active_for={not_active_for:.1f}s "
            #         f"first_loops={first_loops} switch_guard={(last_switch_until-now):.1f}s")

            # 停止判定：起錄已過最短保護，且非活躍/無成長都達門檻，或根本沒有檔案
            if (now - start_epoch >= MIN_RUNTIME_GUARD) and \
               (not_active_for >= GRACE) and \
               (no_growth_for >= max(GRACE, 2.0) or curr_path is None):
                logline("# Auto-detected recording stopped by user (Game Bar).")
                stop("user_stopped", send_hotkey=False)

            # 更新基準
            prev_path, prev_size = curr_path, curr_size

        except Exception as e:
            logline(f"[det] EXC: {e!r}")

        time.sleep(POLL)



# ---------------- Commands ----------------
def _is_gamebar_running():
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq GameBar.exe"],
            creationflags=0x08000000  # CREATE_NO_WINDOW
        ).decode("utf-8", errors="ignore").lower()
        return "gamebar.exe" in out
    except Exception:
        return False

def cmd_start():
    # 先喚起 Game Bar（不阻塞）
    if not _is_gamebar_running():
        try:
            subprocess.Popen(["explorer.exe", "ms-gamebar:"], close_fds=True)
        except Exception:
            pass


    # 1) 立即送熱鍵
    toggle_gamebar_record()

    # 2) 等待「正在錄影」確認（用你貼的 wait_recording_active）
    confirmed = wait_recording_active(timeout=3.0, poll=0.1)

    # 3) 確認後才記錄 start_utc 與啟動 daemon
    session_id = now_local().strftime("%Y%m%d_%H%M%S")
    log_path   = DOCS / f"{session_id}_session.txt"
    start_iso  = now_utc().isoformat(timespec="seconds")
    write_state({"session_id": session_id, "log": str(log_path), "start_utc": start_iso})
    _init_desktop_note(session_id)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"# Likely video folder: {Path.home() / 'Videos' / 'Captures'}\n")
            f.write(("# Recording confirmed by detector.\n" if confirmed 
                     else "# WARNING: recording not confirmed within timeout; timing may be early.\n"))
    except Exception:
        pass

    py = sys.executable
    DETACHED_PROCESS = 0x00000008
    subprocess.Popen([py, __file__, "_daemon", str(log_path), start_iso],
                     creationflags=DETACHED_PROCESS, close_fds=True)

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
        print("Canceled", flush=True); return 0

    if action in ("save", "save_stop"):
        line = f"{elapsed_str:<12} | {now_local():%H:%M:%S.%f}"[:-3] + f" | {note}"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line, flush=True)
        # 也寫到桌面筆記檔
        try:
            _append_desktop_note(st["session_id"], elapsed_str, note)
        except Exception:
            pass


    if action in ("save_stop", "stop"):
        try: FLAG.touch()
        except Exception: pass
        try: toggle_gamebar_record()
        except Exception: pass
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"# Recording session ended at {now_local():%Y-%m-%d %H:%M:%S.%f} (editor)\n")
                f.write(f"# Capture folder: {Path.home() / 'Videos' / 'Captures'}\n")
        except Exception: pass
        _write_detected_video(log_path, start_iso)
        clear_state()
        print("__STOPPED__", flush=True)
        return 0

    return 0
def cmd_stop():
    st = read_state()
    log_path = Path(st["log"]) if st else (DOCS / "unknown_session.txt")
    start_iso = st["start_utc"] if st else now_utc().isoformat(timespec="seconds")

    try: FLAG.touch()                        # 讓 daemon 收尾
    except Exception: pass
    # 不再送 toggle_gamebar_record()，避免誤切回錄影

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"# Recording session ended at {now_local():%Y-%m-%d %H:%M:%S.%f} (manual)\n")
    except Exception: pass

    _write_detected_video(log_path, start_iso)
    # clear_state()
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
