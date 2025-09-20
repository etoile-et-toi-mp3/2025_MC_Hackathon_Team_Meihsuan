# please use python 3.9 ~ 3.12
from operator import index
import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = (
    "3"  # 0 = all logs, 1 = filter INFO, 2 = filter WARNING, 3 = filter ERROR
)
os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"
from absl import logging

logging.set_verbosity(logging.ERROR)

# import libraries
from collections import deque
import cv2
import mediapipe as mp
import pyautogui
import time
import ctypes
from ctypes import wintypes
from comtypes import GUID, IUnknown, COMMETHOD, HRESULT, CoInitialize
from comtypes.client import CreateObject
import win32gui
import numpy as np
import platform
import win32con
import keyboard

cv2.setUseOptimized(True)
cv2.setNumThreads(0)

# --- DPI awareness so screen coords are accurate on HiDPI displays ---
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(
        ctypes.c_void_p(-4)
    )  # PER_MONITOR_AWARE_V2
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

# --- Screen dimensions ---
user32 = ctypes.windll.user32
SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)
hud_buffer = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)

# pyautogui.FAILSAFE = False
# pyautogui.PAUSE = 0.02  # small delay between keys so Alt-Tab UI keeps up

# variables
gesture = None
gesture_start_time = 0
last_seen_time = 0
cancel_cooldown = 1  # seconds
gesture_cancel_time = 0
detected_gesture = None
ok_origin = None
ok_unitpixels = None
app_offset = 0
alt_switch_active = False
last_target_index = None
num_apps_cached = 0  # number of Alt-Tab apps on current desktop

thumb_straight = False
index_straight = False
middle_straight = False
ring_straight = False
pinky_straight = False

VX_REL_THRESH = 3.5  # in hand-widths per second (tune 3.0 ~ 5.0)
DIST_REL_THRESH = 0.6  # must travel at least 0.6 hand-widths within WINDOW_SEC

# variables for SPEED SWIPE DETECTION
VX_THRESH = 1.5
# Pixels/sec threshold to consider a "fast" swipe.
# With 1280x720 frames, ~1000–1600 px/s is a good starting range.

DIST_THRESH = 0.1
# Require the horizontal distance to exceed this many pixels within the window,
# as a fraction of frame width (e.g., 18%)

HORIZ_RATIO = 0.7
# How "horizontal" it must be: |vy| <= HORIZ_RATIO * |vx|

WINDOW_SEC = 0.5
# Time window (seconds) to estimate velocity over recent samples

TRIGGER_COOLDOWN = 2
# Debounce so one swipe only triggers one hotkey

# Keep recent (t, x, y) samples for velocity estimation
track_hist = deque()
last_trigger_time = 0.0

# Cursor trail config
TRAIL_MAX_POINTS = 40  # how many recent points to keep
TRAIL_FADE_SEC = 0.5  # how long a point stays visible
trail = deque(maxlen=TRAIL_MAX_POINTS)

SHOW_PREVIEW = True


# helper functions
def hand_area(landmarks):
    """
    returns length of x, length of y, and area
    """
    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return (max_x - min_x), (max_y - min_y), (max_x - min_x) * (max_y - min_y)


def palm_area(landmarks):
    """
    returns length of x, length of y, and area
    """
    xs = [lm.x for lm in landmarks[0:5]]  # wrist + thumb base + index base + pinky base
    ys = [lm.y for lm in landmarks[0:5]]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return (max_x - min_x), (max_y - min_y), (max_x - min_x) * (max_y - min_y)


def finger_straight(mcp, pip, tip, threshold=0.9):
    v1 = [pip.x - mcp.x, pip.y - mcp.y]
    v2 = [tip.x - pip.x, tip.y - pip.y]
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    norm1 = (v1[0] ** 2 + v1[1] ** 2) ** 0.5
    norm2 = (v2[0] ** 2 + v2[1] ** 2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return False
    cos_sim = dot / (norm1 * norm2)
    return cos_sim >= threshold


def calculate_all_straightness(lm):
    global index_straight, middle_straight, ring_straight, thumb_straight, pinky_straight
    index_straight = finger_straight(lm[5], lm[6], lm[8])
    middle_straight = finger_straight(lm[9], lm[10], lm[12])
    ring_straight = finger_straight(lm[13], lm[14], lm[16])
    thumb_straight = finger_straight(lm[1], lm[2], lm[4])
    pinky_straight = finger_straight(lm[17], lm[18], lm[20])
    return


def is_two_gesture(lm):
    # Returns True if index and middle are pointing in the opposite direction of ring and pinky
    # by comparing their pip-to-tip vectors using dot product
    index_pip, index_tip = lm[6], lm[8]
    middle_pip, middle_tip = lm[10], lm[12]
    ring_pip, ring_tip = lm[14], lm[16]
    pinky_pip, pinky_tip = lm[18], lm[20]

    # Get pip-to-tip vectors
    v_index = [index_tip.x - index_pip.x, index_tip.y - index_pip.y]
    v_middle = [middle_tip.x - middle_pip.x, middle_tip.y - middle_pip.y]
    v_ring = [ring_tip.x - ring_pip.x, ring_tip.y - ring_pip.y]
    v_pinky = [pinky_tip.x - pinky_pip.x, pinky_tip.y - pinky_pip.y]

    # sum_of_ring_pinky_vectors_length = (v_ring[0] ** 2 + v_ring[1] ** 2) ** 0.5 + (v_pinky[0] ** 2 + v_pinky[0] ** 2) ** 0.5
    # print(f"this is sum: {sum_of_ring_pinky_vectors_length}")

    # Normalize vectors
    def normalize(v):
        norm = (v[0] ** 2 + v[1] ** 2) ** 0.5
        if norm == 0:
            return [0, 0]
        return [v[0] / norm, v[1] / norm]

    v_index = normalize(v_index)
    v_middle = normalize(v_middle)
    v_ring = normalize(v_ring)
    v_pinky = normalize(v_pinky)

    im_dot = v_index[0] * v_middle[0] + v_index[1] * v_middle[1]
    mp_dot = v_middle[0] * v_pinky[0] + v_middle[1] * v_pinky[1]
    # rp_dot = v_ring[0] * v_pinky[0] + v_ring[1] * v_pinky[1]

    # print(f"imdot: {im_dot:.3f}, mrdot: {mr_dot:.3f}, rpdot: {rp_dot:.3f}")
    # Threshold for "opposite" direction (dot < -0.7 is about 135 degrees apart)
    return im_dot > 0.5 and mp_dot < -0.6


def is_ok_gesture(lm, close_threshold=0.1):
    # OK: index tip and thumb tip are close, middle, ring, and pinky are straight
    index_tip = lm[8]
    thumb_tip = lm[4]
    dist = ((index_tip.x - thumb_tip.x) ** 2 + (index_tip.y - thumb_tip.y) ** 2) ** 0.5
    if dist > close_threshold:
        return False
    return not index_straight and middle_straight and ring_straight and pinky_straight


def is_three_gesture(lm):
    # Three: index, middle, ring are straight, thumb and pinky are NOT straight
    return (
        index_straight
        and middle_straight
        and ring_straight
        and (not thumb_straight)
        and (not pinky_straight)
    )


def is_four_gesture(lm):
    # Returns True if index, middle, ring, pinky are up, thumb is across palm (not up)
    # Use dot product to check straightness of each finger
    # Thumb should NOT be straight
    # Four: all fingers straight, thumb not straight
    return (
        (not thumb_straight)
        and index_straight
        and middle_straight
        and ring_straight
        and pinky_straight
    )


def decide_gesture(lm):
    calculate_all_straightness(lm)
    if is_two_gesture(lm):
        return "two"
    if is_ok_gesture(lm):
        return "ok"
    if is_four_gesture(lm):
        return "four"
    # if is_three_gesture(lm):
    #     return "three"
    return None


def estimate_velocity(samples):
    """
    samples: list of (t, x, y) with x,y in pixels
    Returns (vx, vy) in px/s computed between the oldest and the newest point,
    and total dx, dy over that window.
    """
    if len(samples) < 2:
        return 0.0, 0.0, 0.0, 0.0
    t0, x0, y0, _ = samples[0]  # the first point
    t1, x1, y1, _ = samples[-1]  # the last point
    # dt = max(1e-3, t1 - t0)
    dt = t1 - t0
    vx = (x1 - x0) / dt
    vy = (y1 - y0) / dt
    return vx, vy, (x1 - x0), (y1 - y0)


def fast_swipe_detector(lm, track_hist, w, h, now):
    global last_trigger_time
    # Only evaluate if we have enough recent samples
    vx, vy, dx, dy = estimate_velocity(list(track_hist))
    hand_wide_portion = max(0.1, palm_area(lm)[0])  # avoid div by zero

    # Check horizontal dominance and speed
    fast_enough = abs(vx) / (hand_wide_portion * SCREEN_W) >= VX_THRESH and abs(dy) <= HORIZ_RATIO * abs(dx)
    diff_side = (track_hist[0][1] - track_hist[0][3]) * (track_hist[-1][1] - track_hist[-1][3]) < 0

    print(f"abs vx: {abs(vx):.3f}, hand width: {hand_wide_portion * SCREEN_W:.3f}, absdy: {abs(dy):.3f}, horiz_ratio x abs(dx): {HORIZ_RATIO * abs(dx):.3f}, fast_enough: {fast_enough}, firstdiff: {track_hist[0][1] - track_hist[0][3]:.3f}, lastdiff: {track_hist[-1][1] - track_hist[-1][3]:.3f}, diff_side: {diff_side}")


    if fast_enough and (now - last_trigger_time) >= TRIGGER_COOLDOWN and diff_side:
        last_trigger_time = now  # reset window so it won't retrigger from same motion
        if vx > 0:
            return 1
        else:
            return -1
    return 0


# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv alt tab section vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
# ---- DWM (skip cloaked windows like UWP background hosts) ----
dwmapi = ctypes.WinDLL("dwmapi")
DWMWA_CLOAKED = 14


def is_cloaked(hwnd):
    cloaked = wintypes.DWORD()
    if (
        dwmapi.DwmGetWindowAttribute(
            wintypes.HWND(hwnd),
            wintypes.DWORD(DWMWA_CLOAKED),
            ctypes.byref(cloaked),
            ctypes.sizeof(cloaked),
        )
        == 0
    ):
        return cloaked.value != 0
    return False


# ---- Alt-Tab eligibility (approx.) ----
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
GW_OWNER = 4


def appears_in_alt_tab(hwnd):
    if not win32gui.IsWindowVisible(hwnd):
        return False
    if not win32gui.GetWindowText(hwnd):
        return False
    if is_cloaked(hwnd):
        return False
    ex = win32gui.GetWindowLong(hwnd, GWL_EXSTYLE)
    if ex & WS_EX_TOOLWINDOW:
        return False
    owner = win32gui.GetWindow(hwnd, GW_OWNER)
    if owner and not (ex & WS_EX_APPWINDOW):
        return False
    return True


# ---- IVirtualDesktopManager for "current desktop only" ----
class IVirtualDesktopManager(IUnknown):
    _iid_ = GUID("{A5CD92FF-29BE-454C-8D04-D82879FB3F1B}")
    _methods_ = [
        COMMETHOD(
            [],
            HRESULT,
            "IsWindowOnCurrentVirtualDesktop",
            (["in"], wintypes.HWND, "topLevelWindow"),
            (["out"], ctypes.POINTER(wintypes.BOOL), "onCurrentDesktop"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetWindowDesktopId",
            (["in"], wintypes.HWND, "topLevelWindow"),
            (["out"], ctypes.POINTER(GUID), "desktopId"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "MoveWindowToDesktop",
            (["in"], wintypes.HWND, "topLevelWindow"),
            (["in"], ctypes.POINTER(GUID), "desktopId"),
        ),
    ]


CoInitialize()
CLSID_VDM = GUID("{AA509086-5CA9-4C25-8F95-589D3C07B48A}")
_vdm = CreateObject(CLSID_VDM, interface=IVirtualDesktopManager)


def _on_current_desktop(hwnd):
    try:
        return bool(_vdm.IsWindowOnCurrentVirtualDesktop(wintypes.HWND(hwnd)))
    except Exception:
        return False


def get_current_desktop_alt_tab_windows():
    result = []

    def cb(hwnd, _):
        if appears_in_alt_tab(hwnd) and _on_current_desktop(hwnd):
            result.append(hwnd)
        return True

    win32gui.EnumWindows(cb, None)
    return result


def start_alt_tab_switcher():
    global alt_switch_active, last_target_index, num_apps_cached
    if alt_switch_active:
        return  # already working

    # Count apps on this desktop and show the switcher
    windows = get_current_desktop_alt_tab_windows()
    num_apps_cached = max(1, len(windows))  # avoid 0

    # Open the switcher: hold Alt, press Tab once (selection starts at index 1)
    pyautogui.keyDown("alt")
    pyautogui.press("tab")
    alt_switch_active = True
    last_target_index = 1
    print(f"[OK] Alt-Tab shown (apps={num_apps_cached})")


def update_alt_tab_selection(target_index, prefer_dir=None):
    """
    Move selection on a circular Alt-Tab ring of size num_apps_cached.
    1-indexed positions. prefer_dir: 'left' or 'right' to resolve direction.
    """
    global last_target_index
    if not alt_switch_active or num_apps_cached <= 1:
        return

    N = num_apps_cached
    # wrap target into 1..N
    target = ((int(target_index) - 1) % N) + 1

    cur = last_target_index or 1  # current selection (1..N)
    if target == cur:
        return

    # distances on the ring
    forward = (target - cur) % N  # steps going right
    backward = (cur - target) % N  # steps going left

    # choose direction
    if prefer_dir == "left":
        key = "left"
        steps = backward if backward != 0 else 0
    elif prefer_dir == "right":
        key = "right"
        steps = forward if forward != 0 else 0
    else:
        # shortest path by default
        if forward <= backward:
            key, steps = "right", forward
        else:
            key, steps = "left", backward

    for _ in range(steps):
        pyautogui.press(key)

    last_target_index = target


def end_alt_tab_switcher():
    global alt_switch_active, last_target_index
    if not alt_switch_active:
        return
    pyautogui.keyUp("alt")  # confirm selection
    alt_switch_active = False
    print("[OK] Alt-Tab confirmed")
    last_target_index = None


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ alt tab section ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# instantiate objects
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    max_num_hands=2,
    static_image_mode=False,
)

cap = cv2.VideoCapture(6, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)  # 1280
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)  # 720

# ---------- Transparent, full-screen, click-through overlay ----------
HUD_WINDOW = "Hand HUD"
hud_hwnd = None


def create_hud_window():
    global hud_hwnd
    try:
        cv2.destroyWindow(HUD_WINDOW)
    except Exception:
        pass

    cv2.namedWindow(HUD_WINDOW, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(HUD_WINDOW, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.setWindowProperty(HUD_WINDOW, cv2.WND_PROP_TOPMOST, 1)

    time.sleep(0.05)  # ensure window exists
    if platform.system() == "Windows":
        hwnd = win32gui.FindWindow(None, HUD_WINDOW)
        if hwnd:
            exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            # Add: WS_EX_LAYERED (transparency), WS_EX_TRANSPARENT (click-through),
            #      WS_EX_TOOLWINDOW (hide from Alt-Tab)
            exstyle |= (
                win32con.WS_EX_LAYERED
                | win32con.WS_EX_TRANSPARENT
                | win32con.WS_EX_TOOLWINDOW
            )
            # Clear WS_EX_APPWINDOW if it exists
            exstyle &= ~win32con.WS_EX_APPWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, exstyle)
            # Make black fully transparent
            win32gui.SetLayeredWindowAttributes(
                hwnd, 0x000000, 0, win32con.LWA_COLORKEY
            )
            hud_hwnd = hwnd


create_hud_window()

# Make it layered + transparent (Windows only)
try:
    import win32con

    time.sleep(0.1)  # ensure window exists
    hud_hwnd = win32gui.FindWindow(None, HUD_WINDOW)
    if hud_hwnd:
        exstyle = win32gui.GetWindowLong(hud_hwnd, win32con.GWL_EXSTYLE)
        # WS_EX_TRANSPARENT = click-through, WS_EX_LAYERED = colorkey transparency
        exstyle |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hud_hwnd, win32con.GWL_EXSTYLE, exstyle)
        # Colorkey = black (0x000000) becomes fully transparent
        win32gui.SetLayeredWindowAttributes(
            hud_hwnd, 0x000000, 0, win32con.LWA_COLORKEY
        )
except Exception:
    pass  # non-Windows or missing pywin32


def draw_cursor(img, x, y, color=(0, 255, 255)):
    cv2.circle(img, (x, y), 10, color, -1)
    cv2.circle(img, (x, y), 20, color, 2)
    cv2.line(img, (x - 30, y), (x + 30, y), color, 1)
    cv2.line(img, (x, y - 30), (x, y + 30), color, 1)


def draw_trail(hud_img, trail_points, now):
    """
    hud_img: your transparent HUD (black = transparent)
    trail_points: deque of (x, y, t)
    now: current time.time()
    """
    if len(trail_points) < 2:
        return

    # Draw older segments thinner and dimmer
    # Color is yellow-ish; older => darker
    for i in range(1, len(trail_points)):
        x0, y0, t0 = trail_points[i - 1]
        x1, y1, t1 = trail_points[i]

        # age of the newer endpoint
        age = now - t1
        a = 1.0 - min(max(age / TRAIL_FADE_SEC, 0.0), 1.0)  # 1..0

        # Skip fully-faded points
        if a <= 0.0:
            continue

        # Thickness and color scale with 'a'
        thickness = max(1, int(10 * a))
        # (B, G, R) — darker as it fades
        color = (int(60 * a), int(220 * a), int(255 * a))

        # Line segment
        cv2.line(
            hud_img,
            (int(x0), int(y0)),
            (int(x1), int(y1)),
            color,
            thickness,
            lineType=cv2.LINE_AA,
        )
        # Small dot at the newer point
        cv2.circle(
            hud_img,
            (int(x1), int(y1)),
            max(2, int(8 * a)),
            color,
            -1,
            lineType=cv2.LINE_AA,
        )


# Extra dots under/above the middle-tip cursor
def draw_gesture_points(hud_img, x, y, gesture, offset_px=80):
    """
    Draw extra points relative to (x,y) based on gesture.
    two  -> one above
    ok   -> two under
    four -> one above + two under
    """
    if not gesture:
        return

    offsets = [(0, 0)]
    # Configure offsets (dx, dy)
    if gesture == "two":
        offsets = [(0, -offset_px)]  # one above
    elif gesture == "ok":
        offsets = [(0, offset_px), (0, 2 * offset_px)]  # two under
    elif gesture == "four":
        offsets = [
            (0, -offset_px),
            (0, offset_px),
            (0, 2 * offset_px),
        ]  # 1 above, 2 under

    # Style: slightly smaller & dimmer than main cursor
    for dx, dy in offsets:
        cx, cy = int(x + dx), int(y + dy)
        cv2.circle(hud_img, (cx, cy), 8, (40, 210, 255), -1, lineType=cv2.LINE_AA)
        cv2.circle(hud_img, (cx, cy), 14, (40, 210, 255), 2, lineType=cv2.LINE_AA)


# main loop
while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Flip frame horizontally (mirror effect)
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    now = time.time()

    # Convert to RGB for MediaPipe
    proc = cv2.resize(frame, (640, int(640 * h / w)))
    rgb = cv2.cvtColor(proc, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    if result.multi_hand_landmarks:
        # Find the biggest hand by bounding box area
        hand = max(
            result.multi_hand_landmarks, key=lambda hl: hand_area(hl.landmark)[2]
        )

        # Draw landmarks and connections for the biggest hand
        mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

        # Draw landmark indices
        for id, lm in enumerate(hand.landmark):
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.putText(
                frame, str(id), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2
            )

        # track middle tip
        x = int(
            hand.landmark[12].x * SCREEN_W
        )  # we make sure these x and y can DEFINITELY reach all screen
        y = int(hand.landmark[12].y * SCREEN_H)
        # x = int(x * (SCREEN_W / w))

        # Drop points older than TRAIL_FADE_SEC (time-based fade)
        trail.append((x, y, now))
        while trail and (now - trail[0][2]) > TRAIL_FADE_SEC:
            trail.popleft()

        # detect gesture first
        detected_gesture = decide_gesture(hand.landmark)
        if detected_gesture:
            # hand is detected and gesture is posed
            if (
                gesture is not None
                and gesture != detected_gesture
                and now - last_seen_time > cancel_cooldown
            ):
                # gesture has changed from one to another
                gesture_cancel_time = now
                ok_origin = None
                if gesture == "ok":
                    # if previous gesture is OK, we need to end the alt-tab session
                    end_alt_tab_switcher()
                print(
                    f"[CANCEL] Gesture '{gesture}' cancelled at {gesture_cancel_time:.2f}"
                )
                print("======================")
                print()
                gesture = detected_gesture
                gesture_start_time = now
                print(
                    f"[DETECT] Gesture '{gesture}' detected at {gesture_start_time:.2f}"
                )
                track_hist.clear()
                trail.clear()

            if gesture is None:
                # no gesture is being recorded currently, so we have the new gesture.
                gesture = detected_gesture
                gesture_start_time = now
                print(
                    f"[DETECT] Gesture '{gesture}' detected at {gesture_start_time:.2f}"
                )
                track_hist.clear()
                trail.clear()

            # simply update the last seen time for the gesture
            if gesture is not None and gesture == detected_gesture:
                last_seen_time = now
        else:
            # hand is detected but no known gesture is posed
            if gesture is not None and now - last_seen_time > cancel_cooldown:
                # already past the cd time -> this gesture should be killed!
                print(
                    f"[cd] Passed the cd time! last gesture was seen {now - last_seen_time} secs ago, killing..."
                )
                gesture_cancel_time = now
                ok_origin = None
                if gesture == "ok":
                    end_alt_tab_switcher()
                print(
                    f"[CANCEL] Gesture '{gesture}' cancelled at {gesture_cancel_time:.2f}"
                )
                print("======================")
                print()
                gesture = None
        
        track_hist.append((now, x, y, hand.landmark[0].x * SCREEN_W))
        # Keep a sliding window of samples (using middle finger, since it is used in all gestures)
        # And trim it to the desired time window (WINDOW_SEC)
        while track_hist and (now - track_hist[0][0]) > WINDOW_SEC:
            track_hist.popleft()
    else:
        # hand is not even detected
        if gesture is not None and now - last_seen_time > cancel_cooldown:
            # already past the cd time -> this gesture should be killed!
            gesture_cancel_time = now
            ok_origin = None
            if gesture == "ok":
                end_alt_tab_switcher()
            print(
                f"[CANCEL] Gesture '{gesture}' cancelled at {gesture_cancel_time:.2f}"
            )
            print("======================")
            print()
            gesture = None

    if gesture is not None and len(track_hist) >= 3:
        # Draw gesture name if active
        cv2.putText(
            frame, gesture, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4
        )

        if gesture == "two" or gesture == "four":
            swipe_direction = fast_swipe_detector(hand.landmark, track_hist, w, h, now)
            if swipe_direction == 1:
                if gesture == "two":
                    # switch to previous page
                    pyautogui.keyDown("alt")
                    pyautogui.press("left")
                    pyautogui.keyUp("alt")
                    print("[SWIPE] FAST LEFT → hotkey fired")
                else:
                    # switch to previous desktop
                    pyautogui.keyDown("ctrl")
                    pyautogui.keyDown("win")
                    pyautogui.press("left")
                    pyautogui.keyUp("win")
                    pyautogui.keyUp("ctrl")
                    print("[SWIPE] FAST LEFT → hotkey fired")
                    time.sleep(0.12)  # let Windows finish switching
                    create_hud_window()  # HUD is now on the new desktop
            elif swipe_direction == -1:
                if gesture == "two":
                    # switch to next page
                    pyautogui.keyDown("alt")
                    pyautogui.press("right")
                    pyautogui.keyUp("alt")
                    print("[SWIPE] FAST RIGHT → hotkey fired")
                else:
                    # switch to next desktop
                    pyautogui.keyDown("ctrl")
                    pyautogui.keyDown("win")
                    pyautogui.press("right")
                    pyautogui.keyUp("win")
                    pyautogui.keyUp("ctrl")
                    print("[SWIPE] FAST RIGHT → hotkey fired")
                    time.sleep(0.12)  # let Windows finish switching
                    create_hud_window()  # HUD is now on the new desktop

        elif gesture == "ok":
            # 1) on first OK frame, set origin and open Alt-Tab
            if ok_origin is None:
                ok_origin = (x, y)  # you compute x,y earlier from landmark[12]
                start_alt_tab_switcher()

            # 2) map finger x to a target index (1..num_apps_cached)
            #    index 1 is the first app after the currently active one
            dx = x - ok_origin[0]
            # positive dx → move right; negative → left
            ok_unitpixels = SCREEN_W / (num_apps_cached * 1.3)
            steps = round(dx / ok_unitpixels)
            target_index = 1 + steps
            prefer_dir = "left" if steps < 0 else ("right" if steps > 0 else None)
            update_alt_tab_selection(target_index, prefer_dir=prefer_dir)

            # (Optional) Visual hint in your preview window
            cv2.line(frame, (ok_origin[0], 0), (ok_origin[0], h), (0, 255, 255), 2)
            cv2.putText(
                frame,
                f"target:{max(1, min(num_apps_cached, int(target_index)))}",
                (30, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )

    # --------- Render transparent overlay with fingertip cursor ----------
    hud = hud_buffer
    hud.fill(0)
    draw_trail(hud, trail, now)
    # Draw the cursor always (or only when gesture == "ok" if you prefer)
    if gesture is not None and x is not None and y is not None:
        # Always draw cursor (or restrict to gesture == "ok")
        draw_cursor(hud, x, y, (0, 255, 255))
        if gesture == detected_gesture:
            draw_gesture_points(hud, x, y, gesture)

        if gesture is not None and gesture == "ok" and ok_origin is not None:
            cv2.line(hud, (x, 0), (x, SCREEN_H), (0, 120, 255), 1)
            cv2.putText(
                hud,
                f"target:{max(1, min(num_apps_cached, int(1 + round((x - ok_origin[0]) / float(ok_unitpixels)))))}",
                (30, 120),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )

    # Black stays transparent; non-black shows up
    cv2.imshow(HUD_WINDOW, hud)
    if SHOW_PREVIEW:
        small = cv2.resize(frame, (640, 360))
        cv2.imshow("Hand Gesture", small)

    if cv2.waitKey(5) & 0xFF == 27 or keyboard.is_pressed("q"):  # Esc to exit
        break

cap.release()
end_alt_tab_switcher()
cv2.destroyAllWindows()
hands.close()

""" TODO: minimalize it! too fat"""
