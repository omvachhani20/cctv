import argparse
import os
import time
from pathlib import Path

import cv2  # type: ignore
from ultralytics import YOLO
import torch

# Initialize global variables
id_mapping = {}
next_person_id = 1
track_frames = {}
previous_positions = {}
saved_images = set()
line_y = 0

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Unique person counting with stable IDs using YOLOv8 + BotSort. "
            "Optimized for near-realtime playback with GPU acceleration."
        )
    )
    parser.add_argument(
        "--source",
        default="NVR 1_ch5_20250613095500_20250613095818.asf",
        help="Video path or camera index (default: sample CCTV file).",
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="YOLOv8 model path (default: yolov8n.pt).",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.35,
        help="Confidence threshold for person detections.",
    )
    parser.add_argument(
        "--save-dir",
        default="dataset",
        help="Directory to save per-ID snapshots (default: dataset).",
    )
    parser.add_argument(
        "--save-video",
        action="store_true",
        help="Save annotated output video to videos/.",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=400,
        help="Frames to keep a track alive without detections.",
    )
    parser.add_argument(
        "--display-every",
        type=int,
        default=2,
        help="Show every Nth frame on screen (default: 2). Inference runs on ALL frames.",
    )
    return parser.parse_args()


def open_source(source):
    if str(source).isdigit():
        return cv2.VideoCapture(int(source))
    return cv2.VideoCapture(source)


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


# Global variables will be initialized in main()

def main():
    global id_mapping, next_person_id, track_frames, previous_positions, saved_images, line_y
    
    args = parse_args()  
    
    track_frames.clear()
    previous_positions.clear()
    id_mapping.clear()
    saved_images.clear()
    next_person_id = 1
    MIN_FRAMES = 10
    track_history = {}
    
    ensure_dir(args.save_dir)
    ensure_dir("videos")

    cap = open_source(args.source)
    if not cap.isOpened():
        raise SystemExit("Video source not found or cannot open.")

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    line_y = height // 2

    # ── FPS: clamp bad values common in CCTV/NVR .asf files ──────────────────
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"[INFO] Detected FPS from file: {fps}")
    if not fps or fps <= 0 or fps > 120:
        fps = 25.0
        print(f"[INFO] FPS clamped to default: {fps}")
    else:
        print(f"[INFO] Using FPS: {fps}")

    frame_duration = 1.0 / fps   # seconds each frame should take at 1x speed

    # ── Video writer ──────────────────────────────────────────────────────────
    writer = None
    if args.save_video:
        out_path = os.path.join("videos", "cctv_unique_person_output.mp4")
        fourcc   = cv2.VideoWriter_fourcc(*"mp4v")
        writer   = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    # ── Load YOLO model on GPU with FP16 (half precision) ────────────────────
    # half=True  → ~2x faster inference on Nvidia GPU, no accuracy loss
    # imgsz=320  → ~3-4x faster than default 640, minimal accuracy loss for CCTV
    # device=0   → use first Nvidia GPU
    print("[INFO] Loading YOLO model...")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Using device: {device}")

    model = YOLO(args.model)
    model.to(device)

    print("[INFO] Model loaded. Starting tracking ...")

    unique_ids        = set()
    last_seen         = {}
  
    counted_ids       = set()
    frame_idx         = 0

    window_name = "CCTV Unique Person Tracker"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, width, height)

    while True:
        frame_start = time.time()   # wall-clock start for this frame

        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        # ── YOLO inference on EVERY frame (keeps count accurate) ─────────────
        # imgsz=320 → smaller resolution for inference only (display stays full res)
        # half=True → FP16 on GPU
        # verbose=False → suppress per-frame console output
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

        # ── Tracking & counting logic (unchanged) ────────────────────────────
        if results and results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes
            ids   = boxes.id.cpu().tolist()
            xyxy  = boxes.xyxy.cpu().tolist()

            for track_id, box in zip(ids, xyxy):
                x1, y1, x2, y2 = map(int, box)
                tid = int(track_id)

                width_box = x2 - x1
                height_box = y2 - y1
                area = width_box * height_box

                # 🔹 FILTER SMALL OBJECTS
                if area < 7000:
                    continue
                if width_box < 40 or height_box < 80:
                    continue

                aspect_ratio = height_box / (width_box + 1)
                if aspect_ratio < 1.2:
                    continue

                last_seen[tid] = 0

                # 🔹 TRACK STABILITY
                track_frames[tid] = track_frames.get(tid, 0) + 1
                if track_frames[tid] < MIN_FRAMES:
                    continue

                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                previous_positions[tid] = (center_x, center_y)

                # store history
                track_history.setdefault(tid, [])
                track_history[tid].append(center_y)

                if len(track_history[tid]) > 5:
                    track_history[tid].pop(0)

                # Step 1: Assign ID (only once)
                if tid not in id_mapping:
                    id_mapping[tid] = next_person_id
                    next_person_id += 1

                real_id = id_mapping[tid]

                # ✅ SAVE IMAGE ONLY ONCE WHEN PERSON IS STABLE
                if real_id not in saved_images:
                    if track_frames[tid] >= MIN_FRAMES:
                        person_crop = frame[y1:y2, x1:x2]

                        # convert BGR → RGB (VERY IMPORTANT for face_recognition)
                        cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)

                        if person_crop.size > 0:
                            snapshot_path = os.path.join(args.save_dir, f"person_{real_id}.jpg")
                            cv2.imwrite(snapshot_path, person_crop)
                            saved_images.add(real_id)

                # Count person once when stable
                if real_id not in counted_ids:
                    counted_ids.add(real_id)
                    unique_ids.add(real_id)

                    # Draw box and ID on frame
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        f"ID:{real_id}",
                        (x1, max(0, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )

        # ── Clean up stale track IDs ──────────────────────────────────────────
        to_remove = []
        for tid in last_seen:
            last_seen[tid] += 1
            if last_seen[tid] > args.max_age:
                to_remove.append(tid)
        for tid in to_remove:
            last_seen.pop(tid, None)
            track_frames.pop(tid, None)
            track_history.pop(tid, None)
            previous_positions.pop(tid, None)

        # ── Overlay info ──────────────────────────────────────────────────────
        cv2.putText(
            frame,
            "Speed: 1.0x",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Unique Persons: {len(unique_ids)}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 200, 255),
            2,
        )

        # ── Display every Nth frame to save time (inference still every frame) ─
        if frame_idx % args.display_every == 0:
            cv2.imshow(window_name, frame)

        if writer is not None:
            writer.write(frame)

        # ── Wall-clock pacing: only wait remaining time after inference ───────
        elapsed    = time.time() - frame_start
        wait_ms    = int(max(1, (frame_duration - elapsed) * 1000))
        key        = cv2.waitKey(wait_ms) & 0xFF

        if key == 27:   # ESC to exit
            break

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()

    print(f"\n[DONE] Total unique persons counted: {len(unique_ids)}")

if __name__ == "__main__":
    main()