# import argparse
# import os
# import time
# from pathlib import Path

# import cv2  # type: ignore
# from ultralytics import YOLO
# import torch

# # Initialize global variables
# id_mapping = {}
# next_person_id = 1
# track_frames = {}
# previous_positions = {}
# saved_images = set()
# line_y = 0

# def parse_args():
#     parser = argparse.ArgumentParser(
#         description=(
#             "Unique person counting with stable IDs using YOLOv8 + BotSort. "
#             "Optimized for near-realtime playback with GPU acceleration."
#         )
#     )
#     parser.add_argument(
#         "--source",
#         default="NVR 1_ch5_20250613095500_20250613095818.asf",
#         help="Video path or camera index (default: sample CCTV file).",
#     )
#     parser.add_argument(
#         "--model",
#         default="yolov8n.pt",
#         help="YOLOv8 model path (default: yolov8n.pt).",
#     )
#     parser.add_argument(
#         "--conf",
#         type=float,
#         default=0.35,
#         help="Confidence threshold for person detections.",
#     )
#     parser.add_argument(
#         "--save-dir",
#         default="dataset",
#         help="Directory to save per-ID snapshots (default: dataset).",
#     )
#     parser.add_argument(
#         "--save-video",
#         action="store_true",
#         help="Save annotated output video to videos/.",
#     )
#     parser.add_argument(
#         "--max-age",
#         type=int,
#         default=400,
#         help="Frames to keep a track alive without detections.",
#     )
#     parser.add_argument(
#         "--display-every",
#         type=int,
#         default=2,
#         help="Show every Nth frame on screen (default: 2). Inference runs on ALL frames.",
#     )
#     return parser.parse_args()


# def open_source(source):
#     if str(source).isdigit():
#         return cv2.VideoCapture(int(source))
#     return cv2.VideoCapture(source)


# def ensure_dir(path):
#     Path(path).mkdir(parents=True, exist_ok=True)


# # Global variables will be initialized in main()

# def main():
#     global id_mapping, next_person_id, track_frames, previous_positions, saved_images, line_y
    
#     args = parse_args()  
    
#     track_frames.clear()
#     previous_positions.clear()
#     id_mapping.clear()
#     saved_images.clear()
#     next_person_id = 1
#     MIN_FRAMES = 10
#     track_history = {}
    
#     ensure_dir(args.save_dir)
#     ensure_dir("videos")

#     cap = open_source(args.source)
#     if not cap.isOpened():
#         raise SystemExit("Video source not found or cannot open.")

#     width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     line_y = height // 2

#     # ── FPS: clamp bad values common in CCTV/NVR .asf files ──────────────────
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     print(f"[INFO] Detected FPS from file: {fps}")
#     if not fps or fps <= 0 or fps > 120:
#         fps = 25.0
#         print(f"[INFO] FPS clamped to default: {fps}")
#     else:
#         print(f"[INFO] Using FPS: {fps}")

#     frame_duration = 1.0 / fps   # seconds each frame should take at 1x speed

#     # ── Video writer ──────────────────────────────────────────────────────────
#     writer = None
#     if args.save_video:
#         out_path = os.path.join("videos", "cctv_unique_person_output.mp4")
#         fourcc   = cv2.VideoWriter_fourcc(*"mp4v")
#         writer   = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

#     # ── Load YOLO model on GPU with FP16 (half precision) ────────────────────
#     # half=True  → ~2x faster inference on Nvidia GPU, no accuracy loss
#     # imgsz=320  → ~3-4x faster than default 640, minimal accuracy loss for CCTV
#     # device=0   → use first Nvidia GPU
#     print("[INFO] Loading YOLO model...")

#     device = "cuda" if torch.cuda.is_available() else "cpu"
#     print(f"[INFO] Using device: {device}")

#     model = YOLO(args.model)
#     model.to(device)

#     print("[INFO] Model loaded. Starting tracking ...")

#     unique_ids        = set()
#     last_seen         = {}
  
#     counted_ids       = set()
#     frame_idx         = 0

#     window_name = "CCTV Unique Person Tracker"
#     cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
#     cv2.resizeWindow(window_name, width, height)

#     while True:
#         frame_start = time.time()   # wall-clock start for this frame

#         ret, frame = cap.read()
#         if not ret:
#             break

#         frame_idx += 1

#         # ── YOLO inference on EVERY frame (keeps count accurate) ─────────────
#         # imgsz=320 → smaller resolution for inference only (display stays full res)
#         # half=True → FP16 on GPU
#         # verbose=False → suppress per-frame console output
#         results = model.track(
#             frame,
#             persist=True,
#             conf=args.conf,
#             classes=[0],
#             tracker="botsort.yaml",
#             imgsz=640,
#             device=device,
#             half=(device == "cuda"),
#             verbose=False,
#         )

#         # ── Tracking & counting logic (unchanged) ────────────────────────────
#         if results and results[0].boxes is not None and results[0].boxes.id is not None:
#             boxes = results[0].boxes
#             ids   = boxes.id.cpu().tolist()
#             xyxy  = boxes.xyxy.cpu().tolist()

#             for track_id, box in zip(ids, xyxy):
#                 x1, y1, x2, y2 = map(int, box)
#                 tid = int(track_id)

#                 width_box = x2 - x1
#                 height_box = y2 - y1
#                 area = width_box * height_box

#                 # 🔹 FILTER SMALL OBJECTS
#                 if area < 7000:
#                     continue
#                 if width_box < 40 or height_box < 80:
#                     continue

#                 aspect_ratio = height_box / (width_box + 1)
#                 if aspect_ratio < 1.2:
#                     continue

#                 last_seen[tid] = 0

#                 # 🔹 TRACK STABILITY
#                 track_frames[tid] = track_frames.get(tid, 0) + 1
#                 if track_frames[tid] < MIN_FRAMES:
#                     continue

#                 center_x = (x1 + x2) // 2
#                 center_y = (y1 + y2) // 2

#                 previous_positions[tid] = (center_x, center_y)

#                 # store history
#                 track_history.setdefault(tid, [])
#                 track_history[tid].append(center_y)

#                 if len(track_history[tid]) > 5:
#                     track_history[tid].pop(0)

#                 # Step 1: Assign ID (only once)
#                 if tid not in id_mapping:
#                     id_mapping[tid] = next_person_id
#                     next_person_id += 1

#                 real_id = id_mapping[tid]

#                 # ✅ SAVE IMAGE ONLY ONCE WHEN PERSON IS STABLE
#                 if real_id not in saved_images:
#                     if track_frames[tid] >= MIN_FRAMES:
#                         person_crop = frame[y1:y2, x1:x2]

#                         # convert BGR → RGB (VERY IMPORTANT for face_recognition)
#                         cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)

#                         if person_crop.size > 0:
#                             snapshot_path = os.path.join(args.save_dir, f"person_{real_id}.jpg")
#                             cv2.imwrite(snapshot_path, person_crop)
#                             saved_images.add(real_id)

#                 # Count person once when stable
#                 if real_id not in counted_ids:
#                     counted_ids.add(real_id)
#                     unique_ids.add(real_id)

#                     # Draw box and ID on frame
#                     cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
#                     cv2.putText(
#                         frame,
#                         f"ID:{real_id}",
#                         (x1, max(0, y1 - 10)),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         0.7,
#                         (0, 255, 0),
#                         2,
#                     )

#         # ── Clean up stale track IDs ──────────────────────────────────────────
#         to_remove = []
#         for tid in last_seen:
#             last_seen[tid] += 1
#             if last_seen[tid] > args.max_age:
#                 to_remove.append(tid)
#         for tid in to_remove:
#             last_seen.pop(tid, None)
#             track_frames.pop(tid, None)
#             track_history.pop(tid, None)
#             previous_positions.pop(tid, None)

#         # ── Overlay info ──────────────────────────────────────────────────────
#         cv2.putText(
#             frame,
#             "Speed: 1.0x",
#             (20, 80),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             0.8,
#             (255, 255, 0),
#             2,
#         )
#         cv2.putText(
#             frame,
#             f"Unique Persons: {len(unique_ids)}",
#             (20, 40),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             0.8,
#             (0, 200, 255),
#             2,
#         )

#         # ── Display every Nth frame to save time (inference still every frame) ─
#         if frame_idx % args.display_every == 0:
#             cv2.imshow(window_name, frame)

#         if writer is not None:
#             writer.write(frame)

#         # ── Wall-clock pacing: only wait remaining time after inference ───────
#         elapsed    = time.time() - frame_start
#         wait_ms    = int(max(1, (frame_duration - elapsed) * 1000))
#         key        = cv2.waitKey(wait_ms) & 0xFF

#         if key == 27:   # ESC to exit
#             break

#     cap.release()
#     if writer is not None:
#         writer.release()
#     cv2.destroyAllWindows()

#     print(f"\n[DONE] Total unique persons counted: {len(unique_ids)}")

# if __name__ == "__main__":
#     main()



import argparse
import os
import time
from pathlib import Path

import cv2  # type: ignore
import numpy as np
from ultralytics import YOLO
import torch

# ── Try importing face_recognition (pip install face-recognition) ─────────────
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
    print("[INFO] face_recognition library found. Face-based deduplication enabled.")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("[WARN] face_recognition not installed. Falling back to body-only tracking.")
    print("       Install: pip install face-recognition")

# ── Global state ──────────────────────────────────────────────────────────────
id_mapping        = {}   # track_id  → real_id
next_person_id    = 1
track_frames      = {}   # track_id  → consecutive stable frames
previous_positions= {}   # track_id  → (cx, cy)
saved_images      = set()
line_y            = 0

# Face recognition state
known_face_encodings = []   # list of 128-d face encodings (one per unique person)
known_face_real_ids  = []   # parallel list: which real_id each encoding belongs to
FACE_MATCH_TOLERANCE = 0.50  # lower = stricter. 0.45–0.55 works well for CCTV


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Unique person counting with stable IDs using YOLOv8 + BotSort + "
            "face_recognition deduplication. Prevents re-counting the same person."
        )
    )
    parser.add_argument("--source",       default="NVR 1_ch5_20250613095500_20250613095818.asf")
    parser.add_argument("--model",        default="yolov8n.pt")
    parser.add_argument("--conf",         type=float, default=0.35)
    parser.add_argument("--save-dir",     default="dataset")
    parser.add_argument("--save-video",   action="store_true")
    parser.add_argument("--max-age",      type=int,   default=400)
    parser.add_argument("--display-every",type=int,   default=2)
    return parser.parse_args()


def open_source(source):
    if str(source).isdigit():
        return cv2.VideoCapture(int(source))
    return cv2.VideoCapture(source)


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def get_face_encoding(bgr_crop):
    """
    Given a BGR crop of a person, return the first face encoding found,
    or None if no face is detected.
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return None

    # face_recognition expects RGB
    rgb = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB)

    # Resize to a small fixed height for speed (face_recognition is CPU-heavy)
    scale = 200 / max(rgb.shape[0], 1)
    if scale < 1.0:
        rgb = cv2.resize(rgb, (0, 0), fx=scale, fy=scale)

    locations = face_recognition.face_locations(rgb, model="hog")
    if not locations:
        return None

    encodings = face_recognition.face_encodings(rgb, locations)
    if not encodings:
        return None

    return encodings[0]   # take the first (largest) face


def find_or_create_real_id(track_id, face_encoding):
    """
    Given a tracker ID and (optionally) a face encoding:
    - If face matches a known person → reuse that person's real_id
    - Otherwise → assign a new real_id
    Returns (real_id, is_new_person)
    """
    global next_person_id, id_mapping, known_face_encodings, known_face_real_ids

    # ── Case 1: track_id already resolved ────────────────────────────────────
    if track_id in id_mapping:
        return id_mapping[track_id], False

    # ── Case 2: try face matching ─────────────────────────────────────────────
    if face_encoding is not None and len(known_face_encodings) > 0:
        distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_idx  = int(np.argmin(distances))
        if distances[best_idx] <= FACE_MATCH_TOLERANCE:
            # This is someone we've seen before — map to their real_id
            real_id = known_face_real_ids[best_idx]
            id_mapping[track_id] = real_id
            print(f"[DEDUP] track_id {track_id} matched existing person {real_id} "
                  f"(dist={distances[best_idx]:.3f})")
            return real_id, False   # not a new person

    # ── Case 3: new person ────────────────────────────────────────────────────
    real_id = next_person_id
    next_person_id += 1
    id_mapping[track_id] = real_id

    if face_encoding is not None:
        known_face_encodings.append(face_encoding)
        known_face_real_ids.append(real_id)

    return real_id, True


def main():
    global id_mapping, next_person_id, track_frames, previous_positions, saved_images, line_y
    global known_face_encodings, known_face_real_ids

    args = parse_args()

    # Reset all state
    track_frames.clear();  previous_positions.clear()
    id_mapping.clear();    saved_images.clear()
    known_face_encodings.clear(); known_face_real_ids.clear()
    next_person_id = 1

    MIN_FRAMES   = 10
    track_history = {}

    ensure_dir(args.save_dir)
    ensure_dir("videos")

    cap = open_source(args.source)
    if not cap.isOpened():
        raise SystemExit("Video source not found or cannot open.")

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    line_y = height // 2

    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"[INFO] Detected FPS from file: {fps}")
    if not fps or fps <= 0 or fps > 120:
        fps = 25.0
        print(f"[INFO] FPS clamped to default: {fps}")

    frame_duration = 1.0 / fps

    writer = None
    if args.save_video:
        out_path = os.path.join("videos", "cctv_unique_person_output.mp4")
        fourcc   = cv2.VideoWriter_fourcc(*"mp4v")
        writer   = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Using device: {device}")

    model = YOLO(args.model)
    model.to(device)
    print("[INFO] Model loaded. Starting tracking ...")

    unique_ids  = set()   # set of real_ids that are truly unique persons
    last_seen   = {}
    counted_ids = set()   # real_ids already counted (no double-count)
    frame_idx   = 0

    # Pending face extraction: track_ids waiting to get a face encoding
    # (we retry a few frames because the face may not be visible immediately)
    face_retry  = {}   # track_id → frames tried

    window_name = "CCTV Unique Person Tracker"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, width, height)

    while True:
        frame_start = time.time()

        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        results = model.track(
            frame,
            persist=True,
            conf=args.conf,
            classes=[0],
            tracker="botsort.yaml",
            imgsz=640,
            device=device,
            half=(device == "cuda"),
            verbose=False,
        )

        if results and results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes
            ids   = boxes.id.cpu().tolist()
            xyxy  = boxes.xyxy.cpu().tolist()

            for track_id, box in zip(ids, xyxy):
                x1, y1, x2, y2 = map(int, box)
                tid = int(track_id)

                # ── Size / aspect filters ─────────────────────────────────────
                w_box = x2 - x1;  h_box = y2 - y1
                if (w_box * h_box) < 7000:       continue
                if w_box < 40 or h_box < 80:     continue
                if h_box / (w_box + 1) < 1.2:   continue

                last_seen[tid] = 0
                track_frames[tid] = track_frames.get(tid, 0) + 1

                if track_frames[tid] < MIN_FRAMES:
                    continue

                # ── Update position history ───────────────────────────────────
                cx = (x1 + x2) // 2;  cy = (y1 + y2) // 2
                previous_positions[tid] = (cx, cy)
                track_history.setdefault(tid, [])
                track_history[tid].append(cy)
                if len(track_history[tid]) > 5:
                    track_history[tid].pop(0)

                # ── Face encoding (try once per track, retry up to 10 frames) ─
                face_enc = None
                if FACE_RECOGNITION_AVAILABLE and tid not in id_mapping:
                    face_retry[tid] = face_retry.get(tid, 0) + 1
                    if face_retry[tid] <= 10:          # try up to 10 frames
                        crop = frame[y1:y2, x1:x2]
                        face_enc = get_face_encoding(crop)

                # ── Resolve real_id (face-deduplicated) ───────────────────────
                real_id, is_new = find_or_create_real_id(tid, face_enc)

                # ── Save snapshot once per real_id ────────────────────────────
                if real_id not in saved_images:
                    crop = frame[y1:y2, x1:x2]
                    if crop.size > 0:
                        path = os.path.join(args.save_dir, f"person_{real_id}.jpg")
                        cv2.imwrite(path, crop)
                        saved_images.add(real_id)

                # ── Count once per real_id ────────────────────────────────────
                if real_id not in counted_ids:
                    counted_ids.add(real_id)
                    unique_ids.add(real_id)
                    print(f"[COUNT] New unique person: {real_id}  "
                          f"(total={len(unique_ids)})")

                # ── Draw bounding box + ID ────────────────────────────────────
                color = (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame, f"ID:{real_id}",
                    (x1, max(0, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2,
                )

        # ── Clean up stale tracks ─────────────────────────────────────────────
        to_remove = [tid for tid, age in last_seen.items()
                     if last_seen.__setitem__(tid, age + 1) or age + 1 > args.max_age]
        # simpler loop:
        stale = []
        for tid in list(last_seen):
            last_seen[tid] += 1
            if last_seen[tid] > args.max_age:
                stale.append(tid)
        for tid in stale:
            last_seen.pop(tid, None)
            track_frames.pop(tid, None)
            track_history.pop(tid, None)
            previous_positions.pop(tid, None)
            face_retry.pop(tid, None)
            # Note: id_mapping entry is kept so face match can still use real_id

        # ── Overlay ───────────────────────────────────────────────────────────
        cv2.putText(frame, f"Unique Persons: {len(unique_ids)}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
        cv2.putText(frame, "Speed: 1.0x",
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        mode_txt = "Mode: Face+Body" if FACE_RECOGNITION_AVAILABLE else "Mode: Body only"
        cv2.putText(frame, mode_txt,
                    (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        if frame_idx % args.display_every == 0:
            cv2.imshow(window_name, frame)

        if writer is not None:
            writer.write(frame)

        elapsed = time.time() - frame_start
        wait_ms = int(max(1, (frame_duration - elapsed) * 1000))
        if cv2.waitKey(wait_ms) & 0xFF == 27:
            break

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()

    print(f"\n[DONE] Total unique persons counted: {len(unique_ids)}")


if __name__ == "__main__":
    main()