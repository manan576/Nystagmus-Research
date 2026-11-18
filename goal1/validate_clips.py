"""
Validation Reviewer — Label oscillation clips as True/False Positives
=====================================================================
Opens each unreviewed video clip from the validation_videos directory,
plays it on loop, and waits for your keypress:

    Y = True Positive  (real oscillation)
    N = False Positive  (not a real oscillation)
    S = Skip (review later)
    Q = Quit

Automatically updates oscillation_log.csv with your label.

Usage:
    python validate_clips.py
"""

import cv2
import csv
import os
import sys
import numpy as np

GOAL1_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_DATA_DIR = os.path.join(GOAL1_DIR, "private_data")
VIDEO_DIR = os.path.join(PRIVATE_DATA_DIR, "validation_videos")
LOG_FILE = os.path.join(PRIVATE_DATA_DIR, "oscillation_log.csv")
WINDOW_NAME = "Validation Review"


def fit_frame_aspect_ratio(frame, target_w, target_h):
    """
    Fit frame into target dimensions while strictly preserving the original aspect ratio.
    Adds black padding (letterboxing/pillarboxing) if target aspect ratio differs.
    Guarantees the original video's proportions are never stretched or distorted.
    """
    h, w = frame.shape[:2]
    if target_w <= 0 or target_h <= 0 or (target_w == w and target_h == h):
        return frame

    scale = min(target_w / w, target_h / h)
    disp_w = max(1, int(w * scale))
    disp_h = max(1, int(h * scale))

    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    resized = cv2.resize(frame, (disp_w, disp_h), interpolation=interp)

    canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    dx = (target_w - disp_w) // 2
    dy = (target_h - disp_h) // 2
    canvas[dy:dy + disp_h, dx:dx + disp_w] = resized
    return canvas


def load_log():
    """Load the CSV log and return rows + header."""
    if not os.path.exists(LOG_FILE):
        print(f"❌ {LOG_FILE} not found. Run OscillationTracker.py first.")
        sys.exit(1)

    with open(LOG_FILE, mode='r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    return header, rows


def save_log(header, rows):
    """Write the full CSV back to disk."""
    with open(LOG_FILE, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def play_video_loop(video_path, hrv_info=None):
    """Play a video on loop until the user presses a key. Returns the key."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  ⚠️  Could not open {video_path}")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30
    delay = int(1000 / fps)

    native_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    native_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        total_frames = 300
    trigger_frame = total_frames // 2

    if native_w <= 0 or native_h <= 0:
        native_w, native_h = 1280, 720

    # Ensure window is initialized with proportional 16:9 dimensions
    rect = cv2.getWindowImageRect(WINDOW_NAME)
    if not rect or rect[2] <= 0 or rect[3] <= 0:
        scale = min(960 / native_w, 540 / native_h) if (native_w > 960 or native_h > 540) else 1.0
        cv2.resizeWindow(WINDOW_NAME, int(native_w * scale), int(native_h * scale))

    print("  Playing on loop... Press Y (true), N (false), S (skip), Q (quit)")

    while True:
        ret, frame = cap.read()

        if not ret:
            # Loop back to start
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        curr_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        h, w = frame.shape[:2]

        # Add instruction overlay (white text with dark outline for crisp readability)
        cv2.putText(frame, "Y=True  N=False  S=Skip  Q=Quit",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, "Y=True  N=False  S=Skip  Q=Quit",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        # Timeline and Phase Overlay (Top-Right)
        if curr_frame < trigger_frame - 6:
            rel_sec = (curr_frame - trigger_frame) / fps
            phase_txt = f"PRE-TRIGGER ({rel_sec:.1f}s)"
            phase_color = (0, 215, 255)  # Amber
        elif curr_frame <= trigger_frame + 6:
            phase_txt = ">>> TRIGGER POINT (t = 0.0s) <<<"
            phase_color = (0, 0, 255)    # Red Alert
        else:
            rel_sec = (curr_frame - trigger_frame) / fps
            phase_txt = f"POST-TRIGGER (+{rel_sec:.1f}s)"
            phase_color = (0, 255, 100)  # Green

        time_txt = f"{curr_frame / fps:.1f}s / {total_frames / fps:.1f}s"
        cv2.putText(frame, time_txt, (w - 200, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, time_txt, (w - 200, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.putText(frame, phase_txt, (w - 410, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, phase_txt, (w - 410, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, phase_color, 2, cv2.LINE_AA)

        # Add HRV data overlay on bottom-left (pure white text with dark outline)
        if hrv_info:
            y_pos = h - 50
            for line in reversed(hrv_info):
                cv2.putText(frame, line, (10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(frame, line, (10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                y_pos -= 35

        # Visual Progress Bar across bottom with Trigger Midpoint
        bar_x = 20
        bar_w = w - 40
        bar_y = h - 18
        bar_h = 7
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)

        progress_pct = max(0.0, min(1.0, curr_frame / max(1, total_frames)))
        progress_w = int(bar_w * progress_pct)
        fill_color = (0, 200, 255) if curr_frame < trigger_frame else (0, 255, 100)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + progress_w, bar_y + bar_h), fill_color, -1)

        # Midpoint indicator line (Trigger point at exactly 5.0s)
        mid_x = bar_x + (bar_w // 2)
        cv2.line(frame, (mid_x, bar_y - 4), (mid_x, bar_y + bar_h + 4), (0, 0, 255), 2)
        cv2.putText(frame, "TRIGGER (0s)", (mid_x - 45, bar_y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 255), 1, cv2.LINE_AA)

        # Check current window dimensions to strictly preserve original aspect ratio
        rect = cv2.getWindowImageRect(WINDOW_NAME)
        if rect and len(rect) >= 4 and rect[2] > 0 and rect[3] > 0:
            win_w, win_h = rect[2], rect[3]
        else:
            win_w, win_h = w, h

        display_frame = fit_frame_aspect_ratio(frame, win_w, win_h)
        cv2.imshow(WINDOW_NAME, display_frame)

        key = cv2.waitKey(delay) & 0xFF

        # Check if user clicked the window's 'X' close button
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            cap.release()
            return 'QUIT'

        if key == ord('y') or key == ord('Y'):
            cap.release()
            return 'TP'
        elif key == ord('n') or key == ord('N'):
            cap.release()
            return 'FP'
        elif key == ord('s') or key == ord('S'):
            cap.release()
            return None  # Skip
        elif key == ord('q') or key == ord('Q') or key == 27:
            cap.release()
            return 'QUIT'

    cap.release()
    return None


def main():
    header, rows = load_log()

    # Find the Validation_Status column index
    try:
        status_idx = header.index("Validation_Status")
    except ValueError:
        print(f"❌ 'Validation_Status' column not found in {LOG_FILE}")
        sys.exit(1)

    # Find the Video_File column index
    try:
        video_idx = header.index("Video_File")
    except ValueError:
        print(f"❌ 'Video_File' column not found in {LOG_FILE}")
        sys.exit(1)

    # Find unreviewed rows (empty Validation_Status, skip background samples)
    unreviewed = [(i, row) for i, row in enumerate(rows)
                  if len(row) > status_idx and row[status_idx].strip() == ""
                  and row[video_idx].strip() != ""]  # Skip BG rows (no video file)

    if not unreviewed:
        print("✅ All clips have been reviewed! Nothing to do.")
        return

    print(f"\n{'='*50}")
    print(f"  Validation Reviewer")
    print(f"  {len(unreviewed)} unreviewed clips found")
    print(f"{'='*50}\n")

    # Initialize review window with proportional 16:9 dimensions (960x540)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 960, 540)

    reviewed_count = 0
    tp_count = 0
    fp_count = 0

    for idx, (row_idx, row) in enumerate(unreviewed):
        video_file = row[video_idx]
        video_path = os.path.join(VIDEO_DIR, video_file)
        timestamp = row[0]

        print(f"\n[{idx + 1}/{len(unreviewed)}] {video_file}  (recorded: {timestamp})")

        if not os.path.exists(video_path):
            print(f"  ⚠️  Video file missing, skipping.")
            continue

        # Build HRV info overlay lines from CSV data
        hrv_info = []
        def safe_get(col_name):
            try:
                idx = header.index(col_name)
                val = row[idx].strip() if idx < len(row) else ""
                return val if val else "--"
            except (ValueError, IndexError):
                return "--"

        rmssd_15 = safe_get("RMSSD_15s")
        rmssd_30 = safe_get("RMSSD_30s")
        rmssd_60 = safe_get("RMSSD_60s")
        bpm = safe_get("BPM")
        quality = safe_get("HRV_Quality")

        hrv_info.append(f"RMSSD: 15s={rmssd_15}  30s={rmssd_30}  60s={rmssd_60} ms")
        hrv_info.append(f"BPM: {bpm}  |  Quality: {quality}")

        # Also print to console
        print(f"  HRV: RMSSD 15s={rmssd_15} 30s={rmssd_30} 60s={rmssd_60}ms | BPM={bpm} | {quality}")

        result = play_video_loop(video_path, hrv_info=hrv_info)

        if result == 'QUIT':
            print("\n  Quitting review session.")
            break
        elif result == 'TP':
            rows[row_idx][status_idx] = 'TP'
            tp_count += 1
            reviewed_count += 1
            print(f"  ✅ Labeled: TRUE POSITIVE")
        elif result == 'FP':
            rows[row_idx][status_idx] = 'FP'
            fp_count += 1
            reviewed_count += 1
            print(f"  ❌ Labeled: FALSE POSITIVE")
        else:
            print(f"  ⏭️  Skipped")

        # Save after each label (in case of crash/quit)
        save_log(header, rows)

    cv2.destroyAllWindows()

    # Summary
    print(f"\n{'='*50}")
    print(f"  Session Complete")
    print(f"  Reviewed: {reviewed_count} clips")
    print(f"  True Positives:  {tp_count}")
    print(f"  False Positives: {fp_count}")
    if tp_count + fp_count > 0:
        precision = tp_count / (tp_count + fp_count) * 100
        print(f"  Detection Precision: {precision:.0f}%")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
