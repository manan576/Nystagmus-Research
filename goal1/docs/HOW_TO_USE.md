# How to Use the Goal 1 Pipeline

This guide explains the complete Goal 1 workflow:

1. Install the software.
2. Connect and test the Polar H9.
3. Record head-oscillation candidates and HRV.
4. Human-validate the recorded clips.
5. Generate session graphs and statistics.

The commands below assume that PowerShell is open in the repository root:

```text
C:\Users\bhate\LOCAL Nystagmus Stress Relation
```

## 1. Initial setup

### Requirements

- Windows with Bluetooth enabled.
- Python 3.11 recommended.
- A working webcam.
- Polar H9 chest strap.
- Internet access for the first dependency installation.

### Create the Python environment

If `.venv` does not already exist:

```powershell
py -3.11 -m venv .venv
```

Install or update the required packages:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\goal1\requirements.txt
```

Using the virtual environment's Python executable directly avoids PowerShell
activation-policy problems.

## 2. Prepare and connect the Polar H9

1. Attach the Polar H9 transmitter to its chest strap.
2. Moisten both electrode areas on the inside of the strap with water.
3. Wear the strap firmly around the chest, directly against the skin.
4. Turn on Bluetooth on the laptop.
5. Close Polar Beat, Polar Flow, and any other application connected to the H9.
   Only one application should control the connection during recording.
6. If Windows displays a pairing prompt, complete it before starting the
   experiment.

The H9 becomes active when the wet electrodes make contact with the skin.

### Test the H9 before recording

Run the standalone Polar test:

```powershell
.\.venv\Scripts\python.exe .\goal1\polar_h9_test.py
```

The test scans for a device whose name starts with `Polar H9`, connects to it,
and subscribes to Bluetooth Heart Rate Measurement notifications. A successful
test should show incoming BPM and RR-interval values. The default test lasts
approximately two minutes so that it can also calculate rolling HRV.

Do not start the full experiment until RR intervals are arriving consistently.

## 3. Prepare for a recording session

Before launching the tracker:

1. Place the laptop or webcam on a stable surface.
2. Sit where the face is clearly visible and well lit.
3. Keep the complete face inside the camera frame.
4. Avoid strong backlighting.
5. Continue wearing the Polar H9.
6. Close applications that may use the webcam, such as Teams, Zoom, or another
   camera application.

## 4. Record oscillations and HRV

Launch the integrated tracker:

```powershell
.\.venv\Scripts\python.exe .\goal1\OscillationTracker.py
```

The program performs the following sequence.

### Step 1: Connect to the H9

The camera opens while a background Bluetooth thread searches for the Polar
H9. If the connection is interrupted during a session, the program attempts to
reconnect automatically.

### Step 2: Complete baseline calibration

After connecting, the program starts a 120-second baseline calibration.

During these two minutes:

- Sit comfortably and remain relaxed.
- Face the camera.
- Breathe normally.
- Avoid deliberate head movements.
- Do not begin the mentally demanding task yet.

Oscillation triggers are disabled during calibration. At the end, the program
stores session-specific 30-second and 60-second RMSSD baselines.

### Step 3: Perform the session activity

After the screen reports that calibration is complete, perform the intended
task. The program then:

- Tracks the horizontal position of the nose landmark.
- Applies Exponential Moving Average smoothing.
- Detects a candidate oscillation after four qualifying direction reversals.
- Uses a six-second trigger cooldown.
- Records ambient HRV every 30 seconds.
- Takes an HRV snapshot when an oscillation candidate is detected.

### Step 4: Save validation footage

For every candidate event, the program saves a ten-second MP4 clip:

- Five seconds before the trigger.
- Five seconds after the trigger.

The files are written to:

```text
goal1/private_data/validation_videos/
```

The corresponding physiological values, timestamps, session ID, and video
filename are appended to:

```text
goal1/private_data/oscillation_log.csv
```

Each run receives an automatically generated session ID such as:

```text
SESS_20261119_143000
```

### Step 5: End the session safely

Click the camera window and press `Esc`. Allow the program to close the camera,
stop Bluetooth notifications, and shut down the BLE thread. Avoid terminating
the terminal forcibly unless the program is unresponsive.

## 5. Validate the recorded clips

The detector identifies candidates, not final ground truth. Every candidate
must be reviewed before it is used in the analysis.

Run:

```powershell
.\.venv\Scripts\python.exe .\goal1\validate_clips.py
```

The reviewer displays only events whose `Validation_Status` is still empty.
Each video repeats until one of these keys is pressed:

| Key | Meaning | CSV label |
|---|---|---|
| `Y` | Genuine head oscillation | `TP` |
| `N` | Normal movement or false detection | `FP` |
| `S` | Uncertain; review later | Unchanged |
| `Q` or `Esc` | Stop the review session | Remaining clips unchanged |

The review window also displays the trigger position and recorded HRV values.
Labels are saved back into:

```text
goal1/private_data/oscillation_log.csv
```

Run the reviewer again at any time to continue with the remaining unreviewed
clips.

## 6. Generate the graphs

Generate the default 30-second RMSSD timeline for every session:

```powershell
.\.venv\Scripts\python.exe .\goal1\analyze_results.py
```

Graphs are saved by default in:

```text
goal1/results/graphs/
```

Only human-validated `TP` oscillations are shown as genuine oscillation markers.
False positives are excluded, and the script warns about unreviewed events.

### Useful graph commands

Generate both 30-second and 60-second timelines:

```powershell
.\.venv\Scripts\python.exe .\goal1\analyze_results.py --window both
```

Generate the stacked comparative graph as well:

```powershell
.\.venv\Scripts\python.exe .\goal1\analyze_results.py --window both --dual
```

Generate graphs for one session only:

```powershell
.\.venv\Scripts\python.exe .\goal1\analyze_results.py --session SESS_YYYYMMDD_HHMMSS
```

Print dataset-wide statistical comparisons in addition to producing graphs:

```powershell
.\.venv\Scripts\python.exe .\goal1\analyze_results.py --stats
```

Specify a different output directory:

```powershell
.\.venv\Scripts\python.exe .\goal1\analyze_results.py --output-dir "C:\path\to\output"
```

Complete validation before interpreting the final graphs or statistical tests.

## 7. Important files

| Location | Purpose |
|---|---|
| `goal1/OscillationTracker.py` | Integrated camera and Polar recording pipeline |
| `goal1/polar_h9_test.py` | Standalone Polar H9 connection test |
| `goal1/validate_clips.py` | Human-in-the-loop video validation |
| `goal1/analyze_results.py` | Graph and statistical analysis |
| `goal1/private_data/oscillation_log.csv` | Real session log and validation labels |
| `goal1/private_data/validation_videos/` | Real event-validation footage |
| `goal1/results/graphs/` | Real-session analysis graphs |
| `goal1/midsem Presentation/` | Synthetic mid-semester demonstration material |

The `midsem Presentation` data is synthetic and must not be reported as real
participant evidence.

## 8. Troubleshooting

### Polar H9 is not found

- Confirm that Bluetooth is enabled.
- Re-moisten the electrode areas and tighten the strap.
- Close Polar applications and disconnect the H9 from other devices.
- Check the H9 battery.
- Run `polar_h9_test.py` again.

### Connected, but no RR intervals appear

- Improve electrode contact with water.
- Confirm the strap is directly against the skin.
- Remain still during the connection test.
- Disconnect other devices that may be consuming the H9 connection.

### Camera does not open

- Close Teams, Zoom, browser camera tabs, and other camera applications.
- Confirm Windows camera permission is enabled for desktop applications.
- Confirm the correct webcam is connected.
- The current tracker uses camera index `0`.

### No oscillations are detected

- Wait until the full baseline calibration finishes.
- Confirm the nose landmark is visible and tracking correctly.
- Improve lighting and camera stability.
- Do not change thresholds merely to force detections; inspect the recorded
  movement and calibration conditions first.

### A video is listed but cannot be opened

- Confirm that the MP4 exists in `goal1/private_data/validation_videos/`.
- Do not rename validation videos independently of the CSV.
- Restore the video and CSV together from the private Goal 1 backup if needed.

### A Python package is missing

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\goal1\requirements.txt
```

## 9. Data-safety rules

- Back up `oscillation_log.csv` and `validation_videos/` together.
- Do not upload `goal1/private_data/` to a public repository.
- Do not edit TP/FP labels manually unless the change is documented.
- Do not mix Goal 2 recordings into the Goal 1 directories.
- Do not use the synthetic mid-semester dataset as empirical evidence.
