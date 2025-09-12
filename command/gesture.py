import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)


# from pygrabber.dshow_graph import FilterGraph
# import cv2

# graph = FilterGraph()
# devices = graph.get_input_devices()

# print("=== 系統偵測到的攝影機 ===")
# for i, name in enumerate(devices):
#     print(f"Index {i}: {name}")

# # 選擇要打開的鏡頭 (例：名稱包含 Logitech)
# selected_index = None
# for i, name in enumerate(devices):
#     if "Logitech" in name:
#         selected_index = i
#         break

# if selected_index is not None:
#     print(f"\n✅ 找到 Logitech 鏡頭，準備開啟 index = {selected_index}")
#     cap = cv2.VideoCapture(selected_index)
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             print("無法讀取畫面")
#             break
#         cv2.imshow(f"Logitech Camera {selected_index}", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#     cap.release()
#     cv2.destroyAllWindows()
# else:
#     print("⚠️ 沒找到 Logitech 鏡頭")


cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

score = 0
prev_area = None
cooldown = 0  # 防止一次出拳加很多分

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # 計算手的 bounding box 面積
            xs = [lm.x for lm in hand_landmarks.landmark]
            ys = [lm.y for lm in hand_landmarks.landmark]
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            area = width * height  # 手的相對大小 (越靠近鏡頭越大)

            if prev_area is not None:
                growth = area - prev_area
                if cooldown == 0 and growth > 0.02:  # 閾值可依實際調整
                    score += 10
                    cooldown = 8

                # 顯示 debug 資訊
                cv2.putText(frame, f"Area: {area:.3f}", (20, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                cv2.putText(frame, f"Growth: {growth:.3f}", (20, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            prev_area = area

    if cooldown > 0:
        cooldown -= 1

    # 畫分數
    cv2.rectangle(frame, (20, 20), (220, 100), (0, 0, 0), -1)
    cv2.putText(frame, f"Score: {score}", (40, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

    cv2.imshow("Boxing Game", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()

