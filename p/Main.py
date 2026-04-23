import cv2
import os
from datetime import datetime
import math

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Camera not found")
    exit()

root_folder = os.getcwd()

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video_writer = None
recording = False

btn_radius = 18

thumb_w, thumb_h = 120, 90
thumb_x, thumb_y = 15, 15

last_photo = None 

frame = None
btn_cx = 0
btn_cy = 0

print("📸click capture button to take photo")
print("🎥 Press 'v' to start/stop video")
print("❌ Press 'q' to quit")

def capture_photo():
    global last_photo

    filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    path = os.path.join(root_folder, filename)
    cv2.imwrite(path, frame)
    last_photo = cv2.resize(frame, (thumb_w, thumb_h))
    print("📸 Photo captured & preview updated")

def mouse_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        distance = math.sqrt((x - btn_cx)**2 + (y - btn_cy)**2)
        if distance <= btn_radius:
            capture_photo()

while True: 
    ret, frame = cap.read()
    if not ret:
        break 

    h, w, _ = frame.shape

    btn_cx = w // 2
    btn_cy = h - 50  
    
    cv2.circle(frame,(btn_cx, btn_cy),btn_radius,(0, 0, 0),)
    if last_photo is not None:
        frame[thumb_y:thumb_y+thumb_h, thumb_x:thumb_x+thumb_w] = last_photo
        cv2.rectangle(
            frame,
            (thumb_x, thumb_y),
            (thumb_x + thumb_w, thumb_y + thumb_h),
            (0, 0, 0),
            2
        )
    cv2.imshow("Camera (Real View)", frame)
    cv2.setMouseCallback("Camera (Real View)", mouse_click)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('v'):
        if not recording:
            filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            video_path = os.path.join(root_folder, filename)

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            video_writer = cv2.VideoWriter(
                video_path, fourcc, 20, (width, height)
            )

            recording = True
            print("🎥 Recording started")

        else:
            recording = False
            video_writer.release()
            print("🛑 Recording stopped & saved")

    elif key == ord('q'):
        print("👋 Closing camera")
        break

    if recording:
        video_writer.write(frame)   

cap.release()
if video_writer:
    video_writer.release()
cv2.destroyAllWindows()