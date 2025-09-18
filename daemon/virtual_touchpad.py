
# --- Suppress TensorFlow, absl, Qt, and Python warnings ---
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 0 = all logs, 1 = info, 2 = warning, 3 = error
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'
import warnings
warnings.filterwarnings('ignore')
try:
    import absl.logging
    absl.logging.set_verbosity(absl.logging.ERROR)
except ImportError:
    pass

import cv2
import mediapipe as mp
import pyautogui
import time

gesture = None
first_x = -1
first_y = -1
final_x = first_x
final_y = first_y

# --- Gesture grace period variables ---
gesture_active = False
gesture_start_time = 0
last_seen_time = 0
cooldown = 0.8  # seconds
gesture_cancel_time = 0

def finger_straight(mcp, pip, tip, threshold=0.8):
    v1 = [pip.x - mcp.x, pip.y - mcp.y]
    v2 = [tip.x - pip.x, tip.y - pip.y]
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    norm1 = (v1[0]**2 + v1[1]**2) ** 0.5
    norm2 = (v2[0]**2 + v2[1]**2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return False
    cos_sim = dot / (norm1 * norm2)
    return cos_sim > threshold

def is_two_gesture(lm):
    # Returns True if thumb, ring tip, and pinky tip are close together,
    # and index/middle are straight (extended)
    thumb_tip = lm[4]
    ring_tip = lm[16]
    pinky_tip = lm[20]
    index_tip, index_pip, index_mcp = lm[8], lm[6], lm[5]
    middle_tip, middle_pip, middle_mcp = lm[12], lm[10], lm[9]

    # Distance between thumb and ring tip
    dist_thumb_ring = ((thumb_tip.x - ring_tip.x) ** 2 + (thumb_tip.y - ring_tip.y) ** 2) ** 0.5
    # Distance between thumb and pinky tip
    dist_thumb_pinky = ((thumb_tip.x - pinky_tip.x) ** 2 + (thumb_tip.y - pinky_tip.y) ** 2) ** 0.5
    # Distance between ring and pinky tip
    dist_ring_pinky = ((ring_tip.x - pinky_tip.x) ** 2 + (ring_tip.y - pinky_tip.y) ** 2) ** 0.5

    # All three should be close (threshold ~0.08)
    close = dist_thumb_ring < 0.08 and dist_thumb_pinky < 0.08 and dist_ring_pinky < 0.08

    # Index and middle should be straight (direction from mcp->pip and pip->tip should be similar)
    index_straight = finger_straight(index_mcp, index_pip, index_tip)
    middle_straight = finger_straight(middle_mcp, middle_pip, middle_tip)

    return close and index_straight and middle_straight

def is_ok_gesture(lm):
    # OK: index tip and thumb tip are close, middle, ring, and pinky are straight
    index_tip = lm[8]
    thumb_tip = lm[4]
    dist = ((index_tip.x - thumb_tip.x) ** 2 + (index_tip.y - thumb_tip.y) ** 2) ** 0.5
    if dist > 0.07:
        return False
    middle_straight = finger_straight(lm[9], lm[10], lm[12])
    ring_straight = finger_straight(lm[13], lm[14], lm[16])
    pinky_straight = finger_straight(lm[17], lm[18], lm[20])
    return middle_straight and ring_straight and pinky_straight

def is_three_gesture(lm):
    # Three: index, middle, ring are straight, thumb and pinky are NOT straight
    index_straight = finger_straight(lm[5], lm[6], lm[8])
    middle_straight = finger_straight(lm[9], lm[10], lm[12])
    ring_straight = finger_straight(lm[13], lm[14], lm[16])
    thumb_straight = finger_straight(lm[1], lm[2], lm[4])
    pinky_straight = finger_straight(lm[17], lm[18], lm[20])
    return index_straight and middle_straight and ring_straight and (not thumb_straight) and (not pinky_straight)

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
    return (not thumb_straight) and index_straight and middle_straight and ring_straight and pinky_straight

def decide_gesture(lm):
    if is_two_gesture(lm):
        return 'two'
    if is_three_gesture(lm):
        return 'three'
    if is_four_gesture(lm):
        return 'four'
    return None

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    max_num_hands=2,
    static_image_mode=False
)

cap = cv2.VideoCapture(5)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

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
        def hand_area(landmarks):
            xs = [lm.x for lm in landmarks]
            ys = [lm.y for lm in landmarks]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            return (max_x - min_x) * (max_y - min_y)
        hand = max(result.multi_hand_landmarks, key=lambda hl: hand_area(hl.landmark))
        # Draw landmarks and connections for the biggest hand
        mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
        # Draw landmark indices
        for id, lm in enumerate(hand.landmark):
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.putText(frame, str(id), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        x = int(hand.landmark[8].x * w)
        y = int(hand.landmark[8].y * h)
        
        detected_gesture = decide_gesture(hand.landmark)

        if detected_gesture:
            if gesture is not None and gesture != detected_gesture and now - last_seen_time > cooldown:
                gesture_cancel_time = now
                print(f"[CANCEL] Gesture '{gesture}' cancelled at {gesture_cancel_time:.2f}")
                print("======================")
                print()
                gesture = detected_gesture
                gesture_start_time = now
                print(f"[DETECT] Gesture '{gesture}' detected at {gesture_start_time:.2f}")
                
            if not gesture_active:
                gesture_active = True
                gesture = detected_gesture
                gesture_start_time = now
                print(f"[DETECT] Gesture '{gesture}' detected at {gesture_start_time:.2f}")
            
            if gesture_active and gesture == detected_gesture:
                # print("last_seen_updated")
                last_seen_time = now
        else:
            if gesture_active and now - last_seen_time > cooldown:
                print(f"overcd! kill!: {now-last_seen_time}")
                gesture_active = False
                gesture_cancel_time = now
                print(f"[CANCEL] Gesture '{gesture}' cancelled at {gesture_cancel_time:.2f}")
                print("======================")
                print()
                gesture = None
    else:
        if gesture_active and now - last_seen_time > cooldown:
            gesture_active = False
            gesture_cancel_time = now
            print(f"[CANCEL] Gesture '{gesture}' cancelled at {gesture_cancel_time:.2f}")
            print("======================")
            print()
            gesture = None

    # Draw gesture name if active
    if gesture_active:
        cv2.putText(frame, gesture, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4)
    cv2.imshow("Hand Gesture", frame)
    
    if cv2.waitKey(5) & 0xFF == 27:  # Esc to exit
        break

cap.release()
