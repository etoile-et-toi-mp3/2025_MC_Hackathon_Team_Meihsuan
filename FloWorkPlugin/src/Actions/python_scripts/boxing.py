import cv2
import mediapipe as mp
import numpy as np
import math
import random
import platform
import pygame

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

pygame.mixer.init()
punch_sound = pygame.mixer.Sound(r"D:\MeiPlugin\src\Actions\python_scripts\punch.wav") 

class TextDisplay:
    def __init__(self):
        self.active_texts = []

    def add_text(self, text, position, color, duration=60):
        self.active_texts.append({
            'text': text,
            'position': position,
            'color': color,
            'duration': duration,
            'original_duration': duration
        })

    def update_and_draw(self, frame):
        texts_to_remove = []
        for i, text_data in enumerate(self.active_texts):
            alpha = text_data['duration'] / text_data['original_duration']
            if alpha > 0:
                color = tuple(int(c * alpha) for c in text_data['color'])
                
                cv2.putText(frame, text_data['text'], 
                            (text_data['position'][0] + 3, text_data['position'][1] + 3),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 8)
                
                cv2.putText(frame, text_data['text'], text_data['position'],
                            cv2.FONT_HERSHEY_SIMPLEX, 2, color, 5)
                text_data['duration'] -= 1
            else:
                texts_to_remove.append(i)
        for i in reversed(texts_to_remove):
            self.active_texts.pop(i)

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

def setup_transparent_window():
    window_name = "Boxing Game"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    if platform.system() == "Windows":
        import win32gui
        import win32con
        import time
        cv2.waitKey(100)
        hwnd = win32gui.FindWindow(None, window_name)
        if hwnd:
            extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                                   extended_style | win32con.WS_EX_LAYERED)
            
            win32gui.SetLayeredWindowAttributes(hwnd, 0x000000, 0, win32con.LWA_COLORKEY)
    return window_name

def create_transparent_background(width, height):
    
    return np.zeros((height, width, 3), dtype=np.uint8)

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

window_name = setup_transparent_window()
text_display = TextDisplay()
score = 0
prev_area = None
prev_compactness = None
cooldown = 0
crack_effects = []
prev_center_x = None

print("Boxing Game Started! Make a fist and punch towards the camera! Press ESC to exit.")

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
    punch_type = None

    if result.multi_hand_landmarks:
        for hand_idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
            handedness = result.multi_handedness[hand_idx].classification[0].label
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
            delta_x = 0 if prev_center_x is None else center_x - prev_center_x

            if prev_area is not None and prev_compactness is not None:
                growth = area - prev_area
                compactness_change = compactness - prev_compactness
                if cooldown == 0 and is_fist_shape and growth > 0.010 and compactness_change < -0.05:
                    score += 10
                    cooldown = 15
                    punch_detected = True
                    punch_sound.play()
                    if handedness == "Left" and delta_x > 40:
                        punch_type = ("LEFT HOOK!", (255, 100, 100))
                    elif handedness == "Right" and delta_x < -40:
                        punch_type = ("RIGHT HOOK!", (100, 255, 100))
                    else:
                        punch_type = ("STRAIGHT!", (100, 100, 255))
                    text_display.add_text(punch_type[0], 
                                          (punch_position[0] - 120, punch_position[1] - 30),
                                          punch_type[1], duration=90)
            prev_area = area
            prev_compactness = compactness
            prev_center_x = center_x

    if punch_detected and punch_position:
        crack_lines = create_crack_lines(punch_position, 
                                         num_lines=random.randint(12, 20), 
                                         max_length=random.randint(150, 250))
        crack_effects.append({
            'lines': crack_lines, 
            'alpha': 1.0, 
            'fade_speed': random.uniform(0.008, 0.015) 
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

    text_display.update_and_draw(display_frame)

    if cooldown > 0:
        cooldown -= 1

    padding = 40  
    per_digit_width = 30  
    score_length = padding * 2 + len(str(score)) * per_digit_width
    score_length = max(score_length, 280) 
    score_bg = display_frame.copy()
    cv2.rectangle(score_bg, (20, 20), (20 + score_length, 100), (50, 50, 50), -1)
    cv2.addWeighted(score_bg, 0.8, display_frame, 0.2, 0, display_frame)
    cv2.rectangle(display_frame, (20, 20), (20 + score_length, 100), (255, 255, 255), 2)

    cv2.putText(display_frame, f"Score: {score}", (38, 78),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 6)
    cv2.putText(display_frame, f"Score: {score}", (35, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    

    cv2.imshow(window_name, display_frame)
    key = cv2.waitKey(1) & 0xFF
    if key == 27: 
        break

cap.release()
cv2.destroyAllWindows()
