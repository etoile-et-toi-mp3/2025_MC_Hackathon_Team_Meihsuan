# python -m pip install screen-brightness-control opencv-python numpy

import cv2
import numpy as np
import screen_brightness_control as sbc
import time

def get_environment_brightness(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return np.mean(gray)

def adjust_screen_brightness(env_brightness):
    target_brightness = np.interp(env_brightness, [30, 200], [10, 100])
    sbc.set_brightness(int(target_brightness))
    print(f"env_brightness: {env_brightness:.2f}, screen_brightness: {int(target_brightness)}%")

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("unable to open camera")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            brightness = get_environment_brightness(frame)
            adjust_screen_brightness(brightness)

            time.sleep(1)

    except KeyboardInterrupt:
        print("end")

    finally:
        cap.release()

if __name__ == "__main__":
    main()
