import argparse
import os
from pathlib import Path

import cv2
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Unique person counting with stable IDs using YOLOv8 + ByteTrack. "
            "Counts each person once per track ID and optionally saves snapshots."
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
        default=30,
        help="Frames to keep a track alive without detections.",
    )
    return parser.parse_args()


def open_source(source):
    if str(source).isdigit():
        return cv2.VideoCapture(int(source))
    return cv2.VideoCapture(source)


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def main():
    args = parse_args()
    ensure_dir(args.save_dir)
    ensure_dir("videos")

    cap = open_source(args.source)
    if not cap.isOpened():
        raise SystemExit("Video source not found or cannot open.")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    writer = None
    if args.save_video:
        out_path = os.path.join("videos", "cctv_unique_person_output.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    model = YOLO(args.model)

    unique_ids = set()
    last_seen = {}

    window_name = "CCTV Unique Person Tracker"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, width, height)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model.track(
            frame,
            persist=True,
            conf=args.conf,
            classes=[0],
            tracker="bytetrack.yaml",
        )

        if results and results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes
            ids = boxes.id.cpu().tolist()
            xyxy = boxes.xyxy.cpu().tolist()

            for track_id, box in zip(ids, xyxy):
                x1, y1, x2, y2 = map(int, box)

                unique_ids.add(int(track_id))
                last_seen[int(track_id)] = 0

                # Save snapshot once per unique ID.
                snapshot_path = os.path.join(args.save_dir, f"person_{int(track_id)}.jpg")
                if not os.path.exists(snapshot_path):
                    crop = frame[y1:y2, x1:x2]
                    if crop.size > 0:
                        cv2.imwrite(snapshot_path, crop)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"ID:{int(track_id)}",
                    (x1, max(0, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

        # Aging for track cleanup.
        to_remove = []
        for tid in last_seen:
            last_seen[tid] += 1
            if last_seen[tid] > args.max_age:
                to_remove.append(tid)
        for tid in to_remove:
            last_seen.pop(tid, None)

        cv2.putText(
            frame,
            f"Total Unique Persons: {len(unique_ids)}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            2,
        )

        cv2.imshow(window_name, frame)

        if writer is not None:
            writer.write(frame)

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()

    print(f"Total unique persons: {len(unique_ids)}")


if __name__ == "__main__":
    main()