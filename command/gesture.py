import cv2
import mediapipe as mp
import numpy as np
import math
import random

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def create_crack_lines(center, num_lines=8, max_length=100):
    lines = []
    for i in range(num_lines):
        angle = random.uniform(0, 2 * math.pi)
        length = random.uniform(20, max_length)
        
        end_x = int(center[0] + math.cos(angle) * length)
        end_y = int(center[1] + math.sin(angle) * length)
        lines.append([(center[0], center[1]), (end_x, end_y)])
        
        if random.random() < 0.6:
            branch_length = length * random.uniform(0.3, 0.7)
            branch_angle = angle + random.uniform(-0.5, 0.5)
            branch_start_ratio = random.uniform(0.3, 0.8)
            
            branch_start_x = int(center[0] + math.cos(angle) * length * branch_start_ratio)
            branch_start_y = int(center[1] + math.sin(angle) * length * branch_start_ratio)
            branch_end_x = int(branch_start_x + math.cos(branch_angle) * branch_length)
            branch_end_y = int(branch_start_y + math.sin(branch_angle) * branch_length)
            
            lines.append([(branch_start_x, branch_start_y), (branch_end_x, branch_end_y)])
    
    return lines

def is_fist(hand_landmarks):
    landmarks = hand_landmarks.landmark
    
    finger_tips = [4, 8, 12, 16, 20]
    finger_pips = [3, 6, 10, 14, 18]
    finger_mcp = [2, 5, 9, 13, 17]
    
    wrist = landmarks[0]
    
    bent_fingers = 0
    
    for i in range(1, 5):
        tip = landmarks[finger_tips[i]]
        pip = landmarks[finger_pips[i]]
        mcp = landmarks[finger_mcp[i]]
        
        tip_to_wrist = ((tip.x - wrist.x) ** 2 + (tip.y - wrist.y) ** 2) ** 0.5
        pip_to_wrist = ((pip.x - wrist.x) ** 2 + (pip.y - wrist.y) ** 2) ** 0.5
        
        if tip_to_wrist < pip_to_wrist:
            bent_fingers += 1
        
        if tip.y > mcp.y:
            bent_fingers += 0.5
    
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    thumb_mcp = landmarks[2]
    
    thumb_to_wrist = ((thumb_tip.x - wrist.x) ** 2 + (thumb_tip.y - wrist.y) ** 2) ** 0.5
    thumb_mcp_to_wrist = ((thumb_mcp.x - wrist.x) ** 2 + (thumb_mcp.y - wrist.y) ** 2) ** 0.5
    
    if thumb_to_wrist < thumb_mcp_to_wrist * 1.1:
        bent_fingers += 1
    
    return bent_fingers >= 3.5

def calculate_hand_compactness(hand_landmarks):
    landmarks = hand_landmarks.landmark
    
    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    
    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)
    
    total_distance = sum(((lm.x - center_x) ** 2 + (lm.y - center_y) ** 2) ** 0.5 for lm in landmarks)
    avg_distance = total_distance / len(landmarks)
    
    compactness = avg_distance / (width * height + 0.001)
    
    return compactness

def draw_screen_cracks(frame, crack_effects):
    for crack_data in crack_effects:
        lines = crack_data['lines']
        alpha = crack_data['alpha']
        
        for line in lines:
            start_point = line[0]
            end_point = line[1]
            
            intensity = int(255 * alpha)
            
            cv2.line(frame, start_point, end_point, (intensity, intensity, 255), 4)
            cv2.line(frame, start_point, end_point, (255, 255, 255), 2)
    
    return frame

def create_transparent_background(width, height):
    background = np.full((height, width, 3), 50, dtype=np.uint8)
    return background

import platform
import os

def setup_transparent_window():
    window_name = "Boxing Game"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    
    if platform.system() == "Windows":
        try:
            import win32gui
            import win32con
            
            import time
            time.sleep(0.5)
            
            hwnd = win32gui.FindWindow(None, window_name)
            if hwnd:
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                                     win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
                win32gui.SetLayeredWindowAttributes(hwnd, 0, 200, win32con.LWA_ALPHA)
        except ImportError:
            pass
    
    return window_name

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

window_name = setup_transparent_window()

score = 0
prev_area = None
prev_compactness = None
cooldown = 0
crack_effects = []

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break
    
    frame = cv2.flip(frame, 1)
    frame_height, frame_width = frame.shape[:2]
    
    display_frame = create_transparent_background(frame_width, frame_height)
    
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)
    
    punch_detected = False
    punch_position = None
    
    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            is_fist_shape = is_fist(hand_landmarks)
            compactness = calculate_hand_compactness(hand_landmarks)
            
            xs = [lm.x for lm in hand_landmarks.landmark]
            ys = [lm.y for lm in hand_landmarks.landmark]
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            area = width * height
            
            center_x = int(sum(xs) / len(xs) * frame_width)
            center_y = int(sum(ys) / len(ys) * frame_height)
            punch_position = (center_x, center_y)
            
            if prev_area is not None and prev_compactness is not None:
                growth = area - prev_area
                compactness_change = compactness - prev_compactness
                
                if (cooldown == 0 and is_fist_shape and 
                    growth > 0.015 and compactness_change < -0.1):
                    score += 10
                    cooldown = 15
                    punch_detected = True
            
            prev_area = area
            prev_compactness = compactness
    
    if punch_detected and punch_position:
        crack_lines = create_crack_lines(punch_position, num_lines=random.randint(8, 15), max_length=random.randint(100, 200))
        crack_effects.append({
            'lines': crack_lines,
            'alpha': 1.0,
            'fade_speed': random.uniform(0.015, 0.03)
        })
    
    crack_effects_to_remove = []
    for i, crack_data in enumerate(crack_effects):
        crack_data['alpha'] -= crack_data['fade_speed']
        if crack_data['alpha'] <= 0:
            crack_effects_to_remove.append(i)
    
    for i in reversed(crack_effects_to_remove):
        crack_effects.pop(i)
    
    if crack_effects:
        display_frame = draw_screen_cracks(display_frame, crack_effects)
    
    if cooldown > 0:
        cooldown -= 1
    
    overlay = display_frame.copy()
    cv2.rectangle(overlay, (20, 20), (280, 100), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, display_frame, 0.3, 0, display_frame)
    cv2.rectangle(display_frame, (20, 20), (280, 100), (255, 255, 255), 2)
    
    cv2.putText(display_frame, f"Score: {score}", (35, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 5)
    cv2.putText(display_frame, f"Score: {score}", (35, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    
    cv2.imshow(window_name, display_frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        break
    elif key == ord('f') or key == ord('F'):
        current_mode = cv2.getWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN)
        if current_mode == cv2.WINDOW_FULLSCREEN:
            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
        else:
            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

cap.release()
cv2.destroyAllWindows()
