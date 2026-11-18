# Goal 1: Stress and Head-Oscillation Pipeline

This directory contains the completed Goal 1 software, documentation, and
supporting assets for investigating whether verified head oscillations occur
when RMSSD is below the participant's session-specific resting baseline.

## Layout

- `OscillationTracker.py` — camera, Polar H9, HRV, and event-capture pipeline.
- `validate_clips.py` — human review of candidate oscillation clips.
- `analyze_results.py` — session summaries and timeline plots.
- `polar_h9_test.py` — standalone Polar H9 connectivity test.
- `private_data/` — real videos and physiological logs; excluded from Git.
- `docs/` — report source, compiled report, and literature notes.
- `results/` — diagrams and analysis outputs.
- `tools/` — scripts that generate diagrams, simulations, and presentations.
- `midsem Presentation/` — synthetic mid-semester presentation data and
  graphs. These are not empirical participant recordings and must not be
  reported as observed data.

## Full usage guide

See [`docs/HOW_TO_USE.md`](docs/HOW_TO_USE.md) for setup, Polar H9 connection,
recording, human validation, graph generation, and troubleshooting instructions.

## Commands

Run these commands from the repository root or from this directory:

```powershell
python goal1/polar_h9_test.py
python goal1/OscillationTracker.py
python goal1/validate_clips.py
python goal1/analyze_results.py
```

All runtime paths are resolved relative to this directory, so the commands do
not depend on the shell's current working directory.
