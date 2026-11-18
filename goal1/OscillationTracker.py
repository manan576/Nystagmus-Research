# ============================================================================
# OscillationTracker.py — Nystagmus Head Oscillation + HRV Stress Pipeline
# ============================================================================
# Integrated system that runs TWO concurrent loops:
#
#   MAIN THREAD (synchronous):
#     OpenCV + MediaPipe face detection → oscillation detection → video/CSV logging
#
#   BLE THREAD (asynchronous):
#     bleak + asyncio → Polar H9 connection → RR interval collection → HRV computation
#
# When an oscillation triggers, the main thread samples the latest HRV data
# from the BLE thread (via a thread-safe lock) and logs it alongside the event.
#
# Architecture:
#   ┌─────────────────────────┐       ┌─────────────────────────┐
#   │   MAIN THREAD           │       │   BLE THREAD            │
#   │   (OpenCV loop)         │       │   (asyncio + bleak)     │
#   │                         │       │                         │
#   │   frame = cap.read()    │       │   connect to Polar H9   │
#   │   detect oscillation    │       │   subscribe to 0x2A37   │
#   │   if trigger:           │       │   on_notify:            │
#   │     hrv = sample_hrv()  │◄──────│     parse BPM, RR       │
#   │     log to CSV          │ Lock  │     update shared data  │
#   └─────────────────────────┘       └─────────────────────────┘
# ============================================================================

import cv2
import mediapipe as mp
import time
from collections import deque
import os
import datetime
import csv
import threading
import asyncio
import struct
import numpy as np
from bleak import BleakScanner, BleakClient

# Resolve all Goal 1 data paths from this script's directory, not the shell's
# current working directory.
GOAL1_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_DATA_DIR = os.path.join(GOAL1_DIR, "private_data")

# ============================================================================
# SECTION 1: BLE / HRV MODULE
# ============================================================================

# --- GATT UUIDs ---
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

# --- BLE Configuration ---
DEVICE_NAME_PREFIX = "Polar H9"
BLE_SCAN_TIMEOUT = 15
RMSSD_WINDOW_SECONDS = 60

# --- Thread-Safe Shared State ---
# The BLE thread writes to this, the main thread reads from it
hr_data_lock = threading.Lock()
hr_shared_state = {
    "connected": False,
    "current_bpm": 0,
    "rr_buffer": deque(maxlen=300),   # (timestamp, rr_ms) tuples
    "bpm_buffer": deque(maxlen=120),  # (timestamp, bpm) tuples
    "last_update": 0,
}


def parse_hr_measurement(data: bytearray):
    """Parse the Heart Rate Measurement GATT characteristic (0x2A37)."""
    flags = data[0]
    hr_format_16bit = bool(flags & 0x01)
    rr_present = bool(flags & 0x10)

    offset = 1
    if hr_format_16bit:
        heart_rate = struct.unpack_from("<H", data, offset)[0]
        offset += 2
    else:
        heart_rate = data[offset]
        offset += 1

    # Skip Energy Expended if present
    if flags & 0x08:
        offset += 2

    rr_intervals_ms = []
    if rr_present:
        while offset + 1 < len(data):
            rr_raw = struct.unpack_from("<H", data, offset)[0]
            rr_ms = (rr_raw / 1024.0) * 1000.0
            rr_intervals_ms.append(rr_ms)
            offset += 2

    return heart_rate, rr_intervals_ms


def compute_rmssd(rr_intervals_ms):
    """Compute RMSSD from a list of RR intervals (ms). Returns -1 if insufficient data."""
    if len(rr_intervals_ms) < 3:
        return -1.0
    rr = np.array(rr_intervals_ms)
    successive_diffs = np.diff(rr)
    if len(successive_diffs) == 0:
        return -1.0
    return round(float(np.sqrt(np.mean(successive_diffs ** 2))), 2)


def compute_sdnn(rr_intervals_ms):
    """Compute SDNN from a list of RR intervals (ms). Returns -1 if insufficient data."""
    if len(rr_intervals_ms) < 3:
        return -1.0
    return round(float(np.std(rr_intervals_ms, ddof=1)), 2)


def sample_hrv():
    """
    Thread-safe function called by the MAIN THREAD when an oscillation triggers.
    Returns a dict of HRV features computed from multiple time windows (15s, 30s, 60s).
    """
    with hr_data_lock:
        connected = hr_shared_state["connected"]
        current_bpm = hr_shared_state["current_bpm"]

        # Snapshot the buffers under lock, compute outside
        now = time.time()
        all_rr = list(hr_shared_state["rr_buffer"])
        all_bpm = list(hr_shared_state["bpm_buffer"])

    # Compute windowed RR intervals for 15s, 30s, 60s
    rr_15s = [rr for ts, rr in all_rr if ts >= now - 15]
    rr_30s = [rr for ts, rr in all_rr if ts >= now - 30]
    rr_60s = [rr for ts, rr in all_rr if ts >= now - 60]

    # Compute RMSSD for each window
    rmssd_15s = compute_rmssd(rr_15s)
    rmssd_30s = compute_rmssd(rr_30s)
    rmssd_60s = compute_rmssd(rr_60s)

    # Compute other features from the 60s window
    rr_count = len(rr_60s)
    sdnn = compute_sdnn(rr_60s)
    mean_rr = round(float(np.mean(rr_60s)), 1) if rr_count >= 1 else -1.0

    windowed_bpm = [bpm for ts, bpm in all_bpm if ts >= now - 60]
    mean_hr = round(float(np.mean(windowed_bpm)), 1) if len(windowed_bpm) >= 1 else -1.0

    # Determine data quality
    if not connected:
        quality = "no_connection"
    elif rr_count >= 30:
        quality = "good"
    elif rr_count >= 10:
        quality = "low"
    else:
        quality = "insufficient"

    return {
        "bpm": mean_hr,
        "rmssd_15s": rmssd_15s,
        "rmssd_30s": rmssd_30s,
        "rmssd_60s": rmssd_60s,
        "mean_rr_60s": mean_rr,
        "sdnn_60s": sdnn,
        "rr_count_60s": rr_count,
        "hrv_quality": quality,
    }


def ble_notification_handler(sender, data: bytearray):
    """BLE callback — fires every ~1 second when the Polar H9 sends data."""
    heart_rate, rr_intervals = parse_hr_measurement(data)
    now = time.time()

    with hr_data_lock:
        hr_shared_state["current_bpm"] = heart_rate
        hr_shared_state["bpm_buffer"].append((now, heart_rate))
        hr_shared_state["last_update"] = now

        for rr_ms in rr_intervals:
            if 300.0 <= rr_ms <= 2000.0:  # Physiological sanity check
                hr_shared_state["rr_buffer"].append((now, rr_ms))


async def ble_main_loop(stop_event: threading.Event):
    """
    The async BLE loop that runs in a background thread.
    Scans for the Polar H9, connects, subscribes, and keeps the connection alive.
    Includes auto-reconnection logic.
    """
    while not stop_event.is_set():
        try:
            # Scan for the Polar H9
            print("[BLE] Scanning for Polar H9...")
            devices = await BleakScanner.discover(timeout=BLE_SCAN_TIMEOUT)
            polar_device = None
            for d in devices:
                if d.name and DEVICE_NAME_PREFIX.lower() in d.name.lower():
                    polar_device = d
                    break

            if polar_device is None:
                print("[BLE] Polar H9 not found. Retrying in 10 seconds...")
                print("[BLE] Make sure the strap is moistened and worn on your chest.")
                for _ in range(100):  # 10 seconds in 0.1s increments
                    if stop_event.is_set():
                        return
                    await asyncio.sleep(0.1)
                continue

            print(f"[BLE] Found: {polar_device.name} [{polar_device.address}]")
            print(f"[BLE] Connecting...")

            # Set up disconnect detection
            disconnect_event = asyncio.Event()

            def on_disconnect(client):
                print("[BLE] Disconnected from Polar H9!")
                with hr_data_lock:
                    hr_shared_state["connected"] = False
                disconnect_event.set()

            async with BleakClient(polar_device.address, timeout=20.0,
                                   disconnected_callback=on_disconnect) as client:
                if not client.is_connected:
                    print("[BLE] Connection failed. Retrying...")
                    continue

                print(f"[BLE] ✅ Connected to {polar_device.name}!")

                with hr_data_lock:
                    hr_shared_state["connected"] = True

                # Subscribe to heart rate notifications
                await client.start_notify(HR_MEASUREMENT_UUID, ble_notification_handler)
                print("[BLE] ✅ Subscribed to Heart Rate Measurement. Streaming data...")

                # Keep alive until disconnect or stop signal
                while not stop_event.is_set() and not disconnect_event.is_set():
                    await asyncio.sleep(0.5)

                # Clean up
                try:
                    if client.is_connected:
                        await client.stop_notify(HR_MEASUREMENT_UUID)
                except Exception:
                    pass

            # If we get here due to disconnect, retry
            if not stop_event.is_set():
                print("[BLE] Will attempt to reconnect in 5 seconds...")
                with hr_data_lock:
                    hr_shared_state["connected"] = False
                for _ in range(50):
                    if stop_event.is_set():
                        return
                    await asyncio.sleep(0.1)

        except Exception as e:
            print(f"[BLE] Error: {e}")
            print("[BLE] Retrying in 10 seconds...")
            with hr_data_lock:
                hr_shared_state["connected"] = False
            for _ in range(100):
                if stop_event.is_set():
                    return
                await asyncio.sleep(0.1)


def ble_thread_entry(stop_event: threading.Event):
    """Entry point for the BLE background thread. Creates its own asyncio event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ble_main_loop(stop_event))
    except Exception as e:
        print(f"[BLE] Thread crashed: {e}")
    finally:
        loop.close()
        print("[BLE] Thread stopped.")


# ============================================================================
# SECTION 2: COMPUTER VISION + OSCILLATION DETECTION (MAIN THREAD)
# ============================================================================

# --- Setup Validation Directories and Logs ---
VIDEO_DIR = os.path.join(PRIVATE_DATA_DIR, "validation_videos")
os.makedirs(VIDEO_DIR, exist_ok=True)

# Updated CSV schema with Session_ID and HRV columns
LOG_FILE = os.path.join(PRIVATE_DATA_DIR, "oscillation_log.csv")
CSV_HEADERS = [
    "Session_ID", "Timestamp", "Video_File", "Validation_Status", "Event_Type",
    "BPM", "RMSSD_15s", "RMSSD_30s", "RMSSD_60s", "Mean_RR_60s", "SDNN_60s",
    "RR_Count_60s", "HRV_Quality"
]

if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADERS)
else:
    # Check if existing CSV has the old schema and migrate
    with open(LOG_FILE, mode='r', newline='') as file:
        reader = csv.reader(file)
        existing_headers = next(reader, [])
    if existing_headers != CSV_HEADERS:
        with open(LOG_FILE, mode='r', newline='') as file:
            reader = csv.reader(file)
            next(reader)  # skip old header
            old_rows = list(reader)
        # Rewrite with new headers, padding/adapting old rows
        with open(LOG_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)
            for row in old_rows:
                if len(row) > 0:
                    if len(row) == len(CSV_HEADERS) - 1:
                        # Prepend default session id if missing Session_ID
                        padded = ["LEGACY"] + row
                    else:
                        padded = row + [""] * (len(CSV_HEADERS) - len(row))
                    writer.writerow(padded)
        print(f"[CSV] Migrated {LOG_FILE} to new schema with Session_ID and HRV columns.")

# --- Setup Camera and MediaPipe ---
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

actual_fps = cap.get(cv2.CAP_PROP_FPS)
if actual_fps <= 0 or actual_fps > 120:
    actual_fps = 30
FPS = int(round(actual_fps))

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh()

# --- Video Buffer Configuration ---
SECONDS_BEFORE = 5
SECONDS_AFTER = 5
PRE_BUFFER_SIZE = int(FPS * SECONDS_BEFORE)
POST_BUFFER_SIZE = int(FPS * SECONDS_AFTER)
frame_buffer = deque(maxlen=PRE_BUFFER_SIZE)

# --- Oscillation Detection Variables ---
prev_nose_x = None
prev_velocity = 0
direction_changes = 0
oscillation_time = 0

# --- Constraints and Filters ---
last_movement_time = time.time()
OSCILLATION_TIMEOUT = 2.0       # Reset direction count if no reversal within 2 seconds
REQUIRED_DIRECTION_CHANGES = 4  # Reduced from 5 to 4 for higher horizontal sensitivity
smoothed_nose_x = None
SMOOTHING_FACTOR = 0.4
VELOCITY_THRESHOLD = 1

# --- Rate Limiting / Cooldown ---
last_save_time = 0
COOLDOWN_SECONDS = 6

# --- Post-Trigger Capture State ---
post_capture_active = False
post_capture_frames = []
post_capture_remaining = 0
pending_save_data = None

# --- Session Configuration & Calibration State ---
SESSION_ID = datetime.datetime.now().strftime("SESS_%Y%m%d_%H%M%S")
CALIBRATION_DURATION = 120        # 120 seconds (2 minutes)
calibration_active = True
calibration_start_time = None     # Starts once Polar H9 connects
calibration_samples_30s = []      # Collects RMSSD_30s during steady-state (elapsed >= 30s)
calibration_samples_60s = []      # Collects RMSSD_60s during steady-state (elapsed >= 60s)
baseline_rmssd_30s = None
baseline_rmssd_60s = None
baseline_bpm = None
last_calib_sample_time = 0

# --- Continuous Ambient Tracking ---
TRACKING_INTERVAL = 30            # Log ambient HRV point every 30 seconds
last_tracking_sample_time = 0

# ============================================================================
# SECTION 3: LAUNCH BLE THREAD AND START MAIN LOOP
# ============================================================================

# Create a stop event to cleanly shut down the BLE thread
ble_stop_event = threading.Event()

# Start the BLE thread
ble_thread = threading.Thread(target=ble_thread_entry, args=(ble_stop_event,), daemon=True)
ble_thread.start()

print(f"\n{'='*70}")
print(f"  NYSTAGMUS HEAD OSCILLATION & HRV TRACKING PIPELINE")
print(f"  Session ID: {SESSION_ID}")
print(f"  Camera FPS: {FPS} (detected: {actual_fps}) | Resolution: 1280x720 (16:9)")
print(f"  Primary Stress Index: RMSSD_30s (Ultra-Short-Term Vagal Tone)")
print(f"  Startup Mode: 120s Baseline Calibration (triggers paused during calibration)")
print(f"  Ambient Tracking: Every {TRACKING_INTERVAL}s logged to {LOG_FILE}")
print(f"  Video Clips: Saving 10s clips (5s pre + 5s post) to /{VIDEO_DIR}")
print(f"  Oscillation Sensitivity: {REQUIRED_DIRECTION_CHANGES} direction reversals (horizontal)")
print(f"  Trigger Cooldown: {COOLDOWN_SECONDS} seconds between oscillation triggers")
print(f"  BLE Interface: Scanning for Polar H9 in background...")
print(f"  Press ESC to exit.")
# --- Display Window Configuration ---
WINDOW_NAME = "Head Movement Tracker"
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, 640, 360)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape

    # Save a CLEAN copy of the frame to the rolling pre-buffer
    clean_frame = frame.copy()
    frame_buffer.append(clean_frame)

    # --- If we're in post-capture mode, collect frames ---
    if post_capture_active:
        post_capture_frames.append(clean_frame.copy())
        post_capture_remaining -= 1

        # Show recording indicator
        cv2.putText(frame, "RECORDING POST-TRIGGER...", (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2)
        progress = 1.0 - (post_capture_remaining / POST_BUFFER_SIZE)
        bar_width = 300
        cv2.rectangle(frame, (50, 120), (50 + bar_width, 140), (100, 100, 100), -1)
        cv2.rectangle(frame, (50, 120), (50 + int(bar_width * progress), 140), (0, 165, 255), -1)

        if post_capture_remaining <= 0:
            # --- SAVE: Stitch pre-buffer + post-capture frames ---
            post_capture_active = False
            save_data = pending_save_data

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(save_data["video_path"], fourcc, FPS, (w, h))

            for buffered_frame in save_data["pre_frames"]:
                out.write(buffered_frame)
            for post_frame in post_capture_frames:
                out.write(post_frame)
            out.release()

            # Sample HRV data and log to CSV
            hrv = save_data["hrv_snapshot"]

            with open(LOG_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    SESSION_ID,
                    save_data["timestamp_str"],
                    save_data["video_filename"],
                    "",                           # Validation_Status (filled later)
                    "OSC",                        # Event_Type: oscillation
                    hrv["bpm"],
                    hrv["rmssd_15s"],
                    hrv["rmssd_30s"],
                    hrv["rmssd_60s"],
                    hrv["mean_rr_60s"],
                    hrv["sdnn_60s"],
                    hrv["rr_count_60s"],
                    hrv["hrv_quality"],
                ])

            total_frames = len(save_data["pre_frames"]) + len(post_capture_frames)
            quality_icon = "✅" if hrv["hrv_quality"] == "good" else "⚠️"
            delta_str = ""
            if baseline_rmssd_30s and baseline_rmssd_30s > 0 and hrv["rmssd_30s"] > 0:
                delta = ((hrv["rmssd_30s"] - baseline_rmssd_30s) / baseline_rmssd_30s) * 100
                delta_str = f" | Stress Delta: {delta:+.1f}%"
            print(f"[{save_data['timestamp_str']}] Oscillation captured! "
                  f"Video: {total_frames} frames ({total_frames / FPS:.1f}s) | "
                  f"RMSSD 30s={hrv['rmssd_30s']}ms (Base: {baseline_rmssd_30s}ms){delta_str} | "
                  f"BPM: {hrv['bpm']} | {quality_icon} {hrv['hrv_quality']}")

            # Cleanup
            post_capture_frames = []
            pending_save_data = None

    # --- MediaPipe Face Detection ---
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            nose = face_landmarks.landmark[1]
            nose_x_raw = int(nose.x * w)
            nose_y = int(nose.y * h)

            # --- EMA Low-Pass Filter ---
            if smoothed_nose_x is None:
                smoothed_nose_x = nose_x_raw
            else:
                smoothed_nose_x = int((SMOOTHING_FACTOR * nose_x_raw) +
                                      ((1 - SMOOTHING_FACTOR) * smoothed_nose_x))

            cv2.circle(frame, (smoothed_nose_x, nose_y), 5, (0, 255, 0), -1)
            cv2.putText(frame, f"Nose: ({smoothed_nose_x}, {nose_y})",
                        (smoothed_nose_x + 10, nose_y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

            # --- Core Oscillation Logic (Active only after calibration) ---
            if not calibration_active:
                if prev_nose_x is not None:
                    velocity = smoothed_nose_x - prev_nose_x

                    if abs(velocity) >= VELOCITY_THRESHOLD:
                        if velocity * prev_velocity < 0:
                            direction_changes += 1
                            last_movement_time = time.time()

                    prev_velocity = velocity

                prev_nose_x = smoothed_nose_x

                # --- Time-Series Constraint ---
                if time.time() - last_movement_time > OSCILLATION_TIMEOUT:
                    direction_changes = 0

                # --- TRIGGER: Oscillation Detected ---
                if direction_changes >= REQUIRED_DIRECTION_CHANGES:
                    oscillation_time = time.time()
                    direction_changes = 0

                    # --- Check Cooldown Timer ---
                    if (not post_capture_active and
                            time.time() - last_save_time >= COOLDOWN_SECONDS):

                        last_save_time = time.time()

                        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        filename_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        video_filename = f"nod_{filename_str}.mp4"
                        video_path = os.path.join(VIDEO_DIR, video_filename)

                        pre_frames = list(frame_buffer)

                        # Sample HRV at the moment of trigger
                        hrv_snapshot = sample_hrv()

                        post_capture_active = True
                        post_capture_remaining = POST_BUFFER_SIZE
                        post_capture_frames = []
                        pending_save_data = {
                            "timestamp_str": timestamp_str,
                            "video_filename": video_filename,
                            "video_path": video_path,
                            "pre_frames": pre_frames,
                            "hrv_snapshot": hrv_snapshot,
                        }

                        delta_txt = ""
                        if baseline_rmssd_30s and baseline_rmssd_30s > 0 and hrv_snapshot["rmssd_30s"] > 0:
                            d = ((hrv_snapshot["rmssd_30s"] - baseline_rmssd_30s) / baseline_rmssd_30s) * 100
                            delta_txt = f" (Delta: {d:+.1f}%)"
                        print(f"[{timestamp_str}] Oscillation triggered! "
                              f"HRV sampled (RMSSD 30s: {hrv_snapshot['rmssd_30s']}ms{delta_txt}). "
                              f"Capturing {SECONDS_AFTER}s of post-trigger footage...")

                    elif post_capture_active:
                        pass
                    else:
                        time_left = int(COOLDOWN_SECONDS - (time.time() - last_save_time))
                        print(f"Nod detected, but system is on cooldown for {time_left} more seconds.")
            else:
                # Triggers paused during calibration
                direction_changes = 0
                prev_velocity = 0

    # --- BLE Connection State Snapshot ---
    with hr_data_lock:
        ble_connected = hr_shared_state["connected"]
        ble_bpm = hr_shared_state["current_bpm"]
        ble_last_update = hr_shared_state["last_update"]

    # --- Calibration Routine & Overlays ---
    if calibration_active:
        if not ble_connected:
            calibration_start_time = None
            cv2.rectangle(frame, (20, 20), (w - 20, 110), (20, 20, 20), -1)
            cv2.rectangle(frame, (20, 20), (w - 20, 110), (0, 0, 255), 2)
            cv2.putText(frame, "WAITING FOR POLAR H9 BLE CONNECTION...", (40, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 100, 255), 2)
            cv2.putText(frame, "Moisten chest strap electrodes and wear securely.", (40, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        else:
            if calibration_start_time is None:
                calibration_start_time = time.time()
                print(f"\n[{SESSION_ID}] Polar H9 connected! Starting {CALIBRATION_DURATION}s baseline calibration...")
                print(f"[{SESSION_ID}] Sit comfortably, face the camera, and breathe naturally.\n")

            elapsed = time.time() - calibration_start_time
            remaining = max(0, int(CALIBRATION_DURATION - elapsed))

            # Collect steady-state rolling samples every 5 seconds
            if (time.time() - last_calib_sample_time >= 5):
                last_calib_sample_time = time.time()
                sample = sample_hrv()
                if elapsed >= 30 and sample["rmssd_30s"] > 0:
                    calibration_samples_30s.append(sample["rmssd_30s"])
                if elapsed >= 60 and sample["rmssd_60s"] > 0:
                    calibration_samples_60s.append(sample["rmssd_60s"])

            # Calibration HUD Banner
            cv2.rectangle(frame, (20, 15), (w - 20, 115), (25, 25, 25), -1)
            cv2.rectangle(frame, (20, 15), (w - 20, 115), (0, 200, 255), 2)
            cv2.putText(frame, f"BASELINE CALIBRATION: {remaining}s REMAINING", (40, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
            cv2.putText(frame, "Please sit relaxed, face screen, and breathe normally. Triggers paused.", (40, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

            # Progress bar
            bar_w = w - 80
            progress = min(1.0, elapsed / CALIBRATION_DURATION)
            cv2.rectangle(frame, (40, 95), (40 + bar_w, 103), (60, 60, 60), -1)
            cv2.rectangle(frame, (40, 95), (40 + int(bar_w * progress), 103), (0, 255, 255), -1)

            if elapsed >= CALIBRATION_DURATION:
                calibration_active = False
                final_hrv = sample_hrv()
                baseline_rmssd_30s = round(float(np.mean(calibration_samples_30s)), 2) if calibration_samples_30s else final_hrv["rmssd_30s"]
                baseline_rmssd_60s = round(float(np.mean(calibration_samples_60s)), 2) if calibration_samples_60s else final_hrv["rmssd_60s"]
                baseline_bpm = final_hrv["bpm"]
                calib_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with open(LOG_FILE, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        SESSION_ID,
                        calib_timestamp,
                        "",
                        "CALIB",
                        "CALIB",
                        baseline_bpm,
                        final_hrv["rmssd_15s"],
                        baseline_rmssd_30s,
                        baseline_rmssd_60s,
                        final_hrv["mean_rr_60s"],
                        final_hrv["sdnn_60s"],
                        final_hrv["rr_count_60s"],
                        final_hrv["hrv_quality"],
                    ])

                print(f"\n{'='*65}")
                print(f"  ✅ BASELINE CALIBRATION COMPLETE for Session: {SESSION_ID}")
                print(f"  Calibrated Baseline RMSSD (30s): {baseline_rmssd_30s:.2f} ms")
                print(f"  Calibrated Baseline RMSSD (60s): {baseline_rmssd_60s:.2f} ms")
                print(f"  Resting Heart Rate:              {baseline_bpm:.1f} bpm")
                print(f"  Active head oscillation tracking is now LIVE!")
                print(f"{'='*65}\n")
                last_tracking_sample_time = time.time()

    else:
        # --- Continuous Ambient Tracking (Every 30s during active session) ---
        if time.time() - last_tracking_sample_time >= TRACKING_INTERVAL:
            last_tracking_sample_time = time.time()
            track_hrv = sample_hrv()
            if track_hrv["hrv_quality"] in ("good", "low"):
                track_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(LOG_FILE, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        SESSION_ID,
                        track_timestamp,
                        "",              # No video for ambient tracking
                        "BG",            # Validation_Status = background
                        "TRACK",         # Event_Type: ambient tracking
                        track_hrv["bpm"],
                        track_hrv["rmssd_15s"],
                        track_hrv["rmssd_30s"],
                        track_hrv["rmssd_60s"],
                        track_hrv["mean_rr_60s"],
                        track_hrv["sdnn_60s"],
                        track_hrv["rr_count_60s"],
                        track_hrv["hrv_quality"],
                    ])
                delta_str = ""
                if baseline_rmssd_30s and baseline_rmssd_30s > 0 and track_hrv["rmssd_30s"] > 0:
                    delta = ((track_hrv["rmssd_30s"] - baseline_rmssd_30s) / baseline_rmssd_30s) * 100
                    delta_str = f" | Delta: {delta:+.1f}%"
                print(f"[TRACK] {track_timestamp} | RMSSD 30s={track_hrv['rmssd_30s']}ms (Base: {baseline_rmssd_30s}ms){delta_str} | BPM={track_hrv['bpm']}")

    # --- HUD: On-Screen Status ---
    if not calibration_active:
        # Top Header HUD
        cv2.putText(frame, f"Session: {SESSION_ID}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        base_text = f"Baseline RMSSD: {baseline_rmssd_30s:.1f}ms" if baseline_rmssd_30s else "Baseline: N/A"
        cv2.putText(frame, base_text, (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        # Nose position indicator
        if smoothed_nose_x is not None:
            cv2.putText(frame, f"Nose: X={smoothed_nose_x}  Y={nose_y}",
                        (10, h - 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Direction changes indicator
        status_color = (0, 255, 0) if direction_changes == 0 else (0, 255, 255)
        if direction_changes >= 2:
            status_color = (0, 165, 255)
        cv2.putText(frame, f"Dir Changes: {direction_changes}/{REQUIRED_DIRECTION_CHANGES}",
                    (10, h - 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

        # Cooldown indicator
        cooldown_remaining = max(0, COOLDOWN_SECONDS - (time.time() - last_save_time))
        if cooldown_remaining > 0 and last_save_time > 0:
            cv2.putText(frame, f"Cooldown: {int(cooldown_remaining)}s",
                        (10, h - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 1)

    # BLE / HRV status indicator (bottom-left)
    if ble_connected and (time.time() - ble_last_update) < 5:
        ble_color = (0, 255, 0)
        ble_text = f"HR: {ble_bpm} bpm"
    elif ble_connected:
        ble_color = (0, 255, 255)
        ble_text = "HR: stale data"
    else:
        ble_color = (0, 0, 255)
        ble_text = "HR: disconnected"

    cv2.putText(frame, ble_text,
                (10, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, ble_color, 2)

    # Oscillation detected flash
    if time.time() - oscillation_time < 1 and post_capture_active:
        cv2.putText(frame, "OSCILLATION DETECTED!", (50, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

    cv2.imshow(WINDOW_NAME, frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

# --- Cleanup ---
print("\nShutting down...")
ble_stop_event.set()  # Signal the BLE thread to stop
cap.release()
cv2.destroyAllWindows()
ble_thread.join(timeout=5)  # Wait up to 5 seconds for BLE thread to finish
print("Done.")
