# Remember to use 3.8 ~ 3.11
import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# LOOP
# Try different indexes and show frames
# for i in range(10):
#     cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # or cv2.CAP_MSMF
#     if cap.isOpened():
#         ret, frame = cap.read()
#         if ret:
#             cv2.imshow(f"Camera {i}", frame)
#             cv2.waitKey(1000)  # Show 1 sec per camera
#         cap.release()

# cv2.destroyAllWindows()
# LOOP

cap = cv2.VideoCapture(5) # this number would vary across diff machines, figure them out with the "LOOP", and change it into your own
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Flip frame horizontally (mirror effect)
    frame = cv2.flip(frame, 1)

    # Convert to RGB for MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            # Draw landmarks and connections
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Draw landmark indices
            for id, lm in enumerate(hand_landmarks.landmark):
                h, w, c = frame.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.putText(frame, str(id), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        ### vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv ###
        # you can do some calculation and detection here.
        ### ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ###

    cv2.imshow("Hand Gesture Tracking", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC key to quit
        break

cap.release()
cv2.destroyAllWindows()
