# please use python 3.9 ~ 3.12
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"   # 0 = all logs, 1 = filter INFO, 2 = filter WARNING, 3 = filter ERROR
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


# pyautogui.FAILSAFE = False
# pyautogui.PAUSE = 0.02  # small delay between keys so Alt-Tab UI keeps up

# variables
gesture = None
gesture_active = False
gesture_start_time = 0
last_seen_time = 0
cancel_cooldown = 0.5  # seconds
gesture_cancel_time = 0
ok_origin = None
ok_unitpixels = 60
app_offset = 0
alt_switch_active = False
last_target_index = None
num_apps_cached = 0    # number of Alt-Tab apps on current desktop

VX_REL_THRESH = 3.5       # in hand-widths per second (tune 3.0 ~ 5.0)
DIST_REL_THRESH = 0.6     # must travel at least 0.6 hand-widths within WINDOW_SEC

# variables for SPEED SWIPE DETECTION
VX_THRESH = 1
# Pixels/sec threshold to consider a "fast" swipe.
# With 1280x720 frames, ~1000–1600 px/s is a good starting range.

DIST_THRESH = 0.1
# Require the horizontal distance to exceed this many pixels within the window,
# as a fraction of frame width (e.g., 18%)

HORIZ_RATIO = 0.55
# How "horizontal" it must be: |vy| <= HORIZ_RATIO * |vx|

WINDOW_SEC = 0.5
# Time window (seconds) to estimate velocity over recent samples

TRIGGER_COOLDOWN = 2
# Debounce so one swipe only triggers one hotkey

# Keep recent (t, x, y) samples for velocity estimation
track_hist = deque()
last_trigger_time = 0.0

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
        norm = (v[0]**2 + v[1]**2) ** 0.5
        if norm == 0:
            return [0, 0]
        return [v[0]/norm, v[1]/norm]

    v_index = normalize(v_index)
    v_middle = normalize(v_middle)
    v_ring = normalize(v_ring)
    v_pinky = normalize(v_pinky)

    im_dot = v_index[0]*v_middle[0] + v_index[1]*v_middle[1]
    mr_dot = v_middle[0]*v_ring[0] + v_middle[1]*v_ring[1]
    rp_dot = v_ring[0]*v_pinky[0] + v_ring[1]*v_pinky[1]

    # print(f"imdot: {im_dot:.3f}, mrdot: {mr_dot:.3f}, rpdot: {rp_dot:.3f}")
    # Threshold for "opposite" direction (dot < -0.7 is about 135 degrees apart)
    return im_dot > 0.5 and mr_dot < -0.75

def is_ok_gesture(lm, close_threshold=0.1):
    # OK: index tip and thumb tip are close, middle, ring, and pinky are straight
    index_tip = lm[8]
    thumb_tip = lm[4]
    dist = ((index_tip.x - thumb_tip.x) ** 2 + (index_tip.y - thumb_tip.y) ** 2) ** 0.5
    if dist > close_threshold:
        return False
    
    index_straight = finger_straight(lm[5], lm[6], lm[8])
    middle_straight = finger_straight(lm[9], lm[10], lm[12])
    ring_straight = finger_straight(lm[13], lm[14], lm[16])
    pinky_straight = finger_straight(lm[17], lm[18], lm[20])
    return (
        not index_straight
        and middle_straight
        and ring_straight
        and pinky_straight
    )

def is_three_gesture(lm):
    # Three: index, middle, ring are straight, thumb and pinky are NOT straight
    index_straight = finger_straight(lm[5], lm[6], lm[8])
    middle_straight = finger_straight(lm[9], lm[10], lm[12])
    ring_straight = finger_straight(lm[13], lm[14], lm[16])
    thumb_straight = finger_straight(lm[1], lm[2], lm[4])
    pinky_straight = finger_straight(lm[17], lm[18], lm[20])
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
    index_straight = finger_straight(lm[5], lm[6], lm[8])
    middle_straight = finger_straight(lm[9], lm[10], lm[12])
    ring_straight = finger_straight(lm[13], lm[14], lm[16])
    pinky_straight = finger_straight(lm[17], lm[18], lm[20])
    # Thumb should NOT be straight
    thumb_straight = finger_straight(lm[1], lm[2], lm[4])
    # Four: all fingers straight, thumb not straight
    return (
        (not thumb_straight)
        and index_straight
        and middle_straight
        and ring_straight
        and pinky_straight
    )

def decide_gesture(lm):
    if is_two_gesture(lm):
        return "two"
    if is_ok_gesture(lm):
        return "ok"
    # if is_three_gesture(lm):
    #     return "three"
    if is_four_gesture(lm):
        return "four"
    return None

def estimate_velocity(samples):
    """
    samples: list of (t, x, y) with x,y in pixels
    Returns (vx, vy) in px/s computed between the oldest and the newest point,
    and total dx, dy over that window.
    """
    if len(samples) < 2:
        return 0.0, 0.0, 0.0, 0.0
    t0, x0, y0, _ = samples[0] # the first point
    t1, x1, y1, _ = samples[-1] # the last point
    # dt = max(1e-3, t1 - t0)
    dt = t1 - t0
    vx = (x1 - x0) / dt
    vy = (y1 - y0) / dt
    return vx, vy, (x1 - x0), (y1 - y0)

def fast_swipe_detector(lm, track_hist, w, h, now):
    global last_trigger_time
    # Only evaluate if we have enough recent samples
    vx, vy, dx, dy = estimate_velocity(list(track_hist))
    hand_wide_portion = hand_area(lm)[0]
    
    # Check horizontal dominance and speed
    fast_enough = abs(vx) / (hand_wide_portion * w) >= VX_THRESH and abs(dy) <= HORIZ_RATIO * abs(dx)
    diff_side = (track_hist[0][1] - track_hist[0][3]) * (track_hist[-1][1] - track_hist[-1][3]) < 0

    if (
        fast_enough
        and (now - last_trigger_time) >= TRIGGER_COOLDOWN
        and diff_side
    ):
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
    if dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(DWMWA_CLOAKED),
        ctypes.byref(cloaked),
        ctypes.sizeof(cloaked),
    ) == 0:
        return cloaked.value != 0
    return False

# ---- Alt-Tab eligibility (approx.) ----
GWL_EXSTYLE      = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW  = 0x00040000
GW_OWNER         = 4
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
    _iid_ = GUID('{A5CD92FF-29BE-454C-8D04-D82879FB3F1B}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'IsWindowOnCurrentVirtualDesktop',
                  (['in'],  wintypes.HWND, 'topLevelWindow'),
                  (['out'], ctypes.POINTER(wintypes.BOOL), 'onCurrentDesktop')),
        COMMETHOD([], HRESULT, 'GetWindowDesktopId',
                  (['in'],  wintypes.HWND, 'topLevelWindow'),
                  (['out'], ctypes.POINTER(GUID), 'desktopId')),
        COMMETHOD([], HRESULT, 'MoveWindowToDesktop',
                  (['in'],  wintypes.HWND, 'topLevelWindow'),
                  (['in'],  ctypes.POINTER(GUID), 'desktopId')),
    ]

CoInitialize()
CLSID_VDM = GUID('{AA509086-5CA9-4C25-8F95-589D3C07B48A}')
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
        return # already working
    
    # Count apps on this desktop and show the switcher
    windows = get_current_desktop_alt_tab_windows()
    num_apps_cached = max(1, len(windows))  # avoid 0
    
    # Open the switcher: hold Alt, press Tab once (selection starts at index 1)
    pyautogui.keyDown('alt')
    pyautogui.press('tab')
    alt_switch_active = True
    last_target_index = 1
    print(f"[OK] Alt-Tab shown (apps={num_apps_cached})")

def update_alt_tab_selection(target_index):
    """Move selection from last_target_index → target_index using Left/Right."""
    global last_target_index
    if not alt_switch_active or num_apps_cached <= 1:
        return
    
    target_index = max(1, min(num_apps_cached, int(target_index)))
    diff = target_index - (last_target_index or 1)
    if diff == 0:
        return
    
    key = 'right' if diff > 0 else 'left'
    for _ in range(abs(diff)):
        pyautogui.press(key)
    last_target_index = target_index

def end_alt_tab_switcher():
    global alt_switch_active, last_target_index
    if not alt_switch_active:
        return
    pyautogui.keyUp('alt')     # confirm selection
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

cap = cv2.VideoCapture(5)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

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
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    if result.multi_hand_landmarks:
        # Find the biggest hand by bounding box area
        hand = max(result.multi_hand_landmarks, key=lambda hl: hand_area(hl.landmark)[2])
        
        # Draw landmarks and connections for the biggest hand
        mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
        
        # Draw landmark indices
        for id, lm in enumerate(hand.landmark):
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.putText(frame, str(id), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # Keep a sliding window of samples (using middle finger, since it is used in all gestures)
        x = int(hand.landmark[12].x * w)
        y = int(hand.landmark[12].y * h)

        # And trim it to the desired time window (WINDOW_SEC)
        while track_hist and (now - track_hist[0][0]) > WINDOW_SEC:
            track_hist.popleft()

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
                end_alt_tab_switcher()
                print(f"[CANCEL] Gesture '{gesture}' cancelled at {gesture_cancel_time:.2f}")
                print("======================")
                print()
                gesture = detected_gesture
                gesture_start_time = now
                print(f"[DETECT] Gesture '{gesture}' detected at {gesture_start_time:.2f}")
                track_hist.clear()

            if not gesture_active:
                # no gesture is being recorded currently, so we have the new gesture.
                gesture_active = True
                gesture = detected_gesture
                gesture_start_time = now
                print(f"[DETECT] Gesture '{gesture}' detected at {gesture_start_time:.2f}")
                track_hist.clear()

            # simply update the last seen time for the gesture
            if gesture_active and gesture == detected_gesture:
                track_hist.append((now, x, y, hand.landmark[0].x * w))
                last_seen_time = now
        else:
            # hand is detected but no known gesture is posed
            if gesture_active and now - last_seen_time > cancel_cooldown:
                # already past the cd time -> this gesture should be killed!
                print(f"[cd] Passed the cd time! last gesture was seen {now - last_seen_time} secs ago, killing...")
                gesture_active = False
                gesture_cancel_time = now
                ok_origin = None
                end_alt_tab_switcher()
                print(f"[CANCEL] Gesture '{gesture}' cancelled at {gesture_cancel_time:.2f}")
                print("======================")
                print()
                gesture = None
    else:
        # hand is not even detected
        if gesture_active and now - last_seen_time > cancel_cooldown:
            # already past the cd time -> this gesture should be killed!
            gesture_active = False
            gesture_cancel_time = now
            ok_origin = None
            end_alt_tab_switcher()
            print(f"[CANCEL] Gesture '{gesture}' cancelled at {gesture_cancel_time:.2f}")
            print("======================")
            print()
            gesture = None

    if gesture_active and len(track_hist) >= 3:
        # Draw gesture name if active
        cv2.putText(frame, gesture, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4)
        
        if gesture == "two":
            swipe_direction = fast_swipe_detector(hand.landmark, track_hist, w, h, now)
            if swipe_direction == 1:
                # switch to previous page
                pyautogui.keyDown("alt");pyautogui.press("left");pyautogui.keyUp("alt")
                print("[SWIPE] FAST LEFT → hotkey fired")
            elif swipe_direction == -1:
                # switch to next page
                pyautogui.keyDown("alt");pyautogui.press("right");pyautogui.keyUp("alt")
                print("[SWIPE] FAST RIGHT → hotkey fired")

        elif gesture == "four":
            swipe_direction = fast_swipe_detector(hand.landmark, track_hist, w, h, now)
            if swipe_direction == 1:
                # switch to previous desktop
                pyautogui.keyDown("ctrl");pyautogui.keyDown("win");pyautogui.press("left")
                pyautogui.keyUp("win");pyautogui.keyUp("ctrl")
                print("[SWIPE] FAST LEFT → hotkey fired")
            elif swipe_direction == -1:
                # switch to next desktop
                pyautogui.keyDown("ctrl");pyautogui.keyDown("win");pyautogui.press("right")
                pyautogui.keyUp("win");pyautogui.keyUp("ctrl")
                print("[SWIPE] FAST RIGHT → hotkey fired")
                
        elif gesture == "ok":
            # 1) on first OK frame, set origin and open Alt-Tab
            if ok_origin is None:
                ok_origin = (x, y)  # you compute x,y earlier from landmark[12]
                start_alt_tab_switcher()

            # 2) map finger x to a target index (1..num_apps_cached)
            #    index 1 is the first app after the currently active one
            dx = x - ok_origin[0]
            # positive dx → move right; negative → left
            steps = round(dx / float(ok_unitpixels))
            target_index = 1 + steps # 1-indexed
            update_alt_tab_selection(target_index)

            # (Optional) Visual hint in your preview window
            cv2.line(frame, (ok_origin[0], 0), (ok_origin[0], h), (0, 255, 255), 2)
            cv2.putText(frame, f"target:{max(1, min(num_apps_cached, int(target_index)))}",
                        (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)

    cv2.imshow("Hand Gesture", frame)

    if cv2.waitKey(5) & 0xFF == 27:  # Esc to exit
        break

cap.release()

""" TODO: transparent glass window with pointer tracker as animation """
