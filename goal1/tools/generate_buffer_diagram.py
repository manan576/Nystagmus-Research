"""
Generate Publication Diagram: Dual Rolling Buffers in Telemetry Pipeline
========================================================================
Illustrates:
1. Panel A: R-R Interval Rolling Buffer (Capacity: 300 beats) for real-time
   multi-window HRV (RMSSD) extraction from asynchronous Polar H9 BLE ECG.
2. Panel B: Pre-Trigger Video Frame Rolling Buffer (Capacity: 150 frames / 5s at 30 FPS)
   for zero-loss retroactive ground-truth recording upon oscillation detection.

Outputs:
- diagram_rolling_buffers.png (300 DPI, academic publication quality)
"""

import os
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ArrowStyle

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
GOAL1_DIR = os.path.dirname(TOOLS_DIR)
DIAGRAM_DIR = os.path.join(GOAL1_DIR, "results", "diagrams")

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def create_diagram():
    fig = plt.figure(figsize=(15, 9.5), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Overall Background
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    # Master Title
    ax.text(7.5, 9.65, "Dual Rolling Buffer Architecture for Continuous Biosignal & Video Telemetry",
            ha="center", va="center", fontsize=15, fontweight="bold", color="#002060")
    ax.text(7.5, 9.32, "High-efficiency $O(1)$ circular memory structures for asynchronous ECG streaming and retroactive event capture",
            ha="center", va="center", fontsize=10.5, fontstyle="italic", color="#4A5568")

    # =========================================================================
    # PANEL A: R-R INTERVAL ROLLING BUFFER (Top Half)
    # =========================================================================
    panel_a_bg = FancyBboxPatch((0.4, 4.95), 14.2, 4.15,
                                boxstyle="round,pad=0.15,rounding_size=0.12",
                                facecolor="#F8FAFC", edgecolor="#CBD5E0", linewidth=1.2)
    ax.add_patch(panel_a_bg)

    # Panel A Header
    ax.text(0.7, 8.85, "(A) Asynchronous R-R Interval Rolling Buffer", fontsize=12.5, fontweight="bold", color="#002060")
    ax.text(5.9, 8.85, "[collections.deque(maxlen=300)]", fontsize=10.5, fontfamily="monospace", fontweight="bold", color="#B41414")
    ax.text(0.7, 8.58, "Maintains a fixed 300-beat memory pool to compute sliding 15s, 30s, and 60s vagal stress metrics without memory leaks.",
            fontsize=9.2, color="#4A5568")

    # 1. ECG Input Stream (Left)
    input_box = FancyBboxPatch((0.7, 6.7), 2.3, 1.4,
                               boxstyle="round,pad=0.1,rounding_size=0.08",
                               facecolor="#FFF5F5", edgecolor="#FEB2B2", linewidth=1.2)
    ax.add_patch(input_box)
    ax.text(1.85, 7.82, "Polar H9 BLE ECG", ha="center", fontsize=10, fontweight="bold", color="#9B2C2C")
    ax.text(1.85, 7.48, "GATT 0x2A37 (~1 Hz)", ha="center", fontsize=8.5, color="#742A2A")
    ax.text(1.85, 7.15, "Incoming $RR_t$ (ms):", ha="center", fontsize=8.2, fontweight="bold", color="#2D3748")
    ax.text(1.85, 6.85, "792, 804, 785, 810...", ha="center", fontsize=8.5, fontfamily="monospace", color="#C53030")

    # Arrow Input -> Deque
    ax.annotate("", xy=(3.4, 7.4), xytext=(3.0, 7.4),
                arrowprops=dict(arrowstyle="->", lw=2.0, color="#C53030"))
    ax.text(3.2, 7.62, "append()", ha="center", fontsize=8, fontfamily="monospace", fontweight="bold", color="#C53030")

    # 2. Circular Deque Visualization (Center)
    deque_frame = FancyBboxPatch((3.5, 6.4), 6.6, 1.9,
                                 boxstyle="round,pad=0.1,rounding_size=0.1",
                                 facecolor="#EDF2F7", edgecolor="#A0AEC0", linewidth=1.2)
    ax.add_patch(deque_frame)
    ax.text(6.8, 8.08, "Circular Double-Ended Queue (Capacity = 300 Beats)",
            ha="center", fontsize=9.5, fontweight="bold", color="#2D3748")

    # Slot Boxes (Representing slots 0 to 299)
    slots_data = [
        ("t-0", "810ms", "#E2E8F0", "#2D3748"),
        ("t-1", "785ms", "#E2E8F0", "#2D3748"),
        ("t-2", "804ms", "#E2E8F0", "#2D3748"),
        ("t-3", "792ms", "#E2E8F0", "#2D3748"),
        ("...", "...", "#EDF2F7", "#718096"),
        ("t-k", "740ms", "#E2E8F0", "#2D3748"),
        ("...", "...", "#EDF2F7", "#718096"),
        ("t-298", "825ms", "#FEEBC8", "#7B341E"),
        ("t-299", "830ms", "#FED7D7", "#9B2C2C")
    ]
    slot_w = 0.62
    slot_h = 1.0
    start_x = 3.7
    for idx, (label_top, val, bg_c, txt_c) in enumerate(slots_data):
        curr_x = start_x + idx * (slot_w + 0.08)
        sb = FancyBboxPatch((curr_x, 6.6), slot_w, slot_h,
                            boxstyle="round,pad=0.04,rounding_size=0.04",
                            facecolor=bg_c, edgecolor="#A0AEC0", linewidth=0.9)
        ax.add_patch(sb)
        ax.text(curr_x + slot_w/2, 7.35, label_top, ha="center", va="center", fontsize=7.2, color="#4A5568")
        ax.text(curr_x + slot_w/2, 6.95, val, ha="center", va="center", fontsize=7.2, fontweight="bold", color=txt_c)

    # Eviction Arrow (Right)
    ax.annotate("", xy=(10.7, 7.1), xytext=(10.2, 7.1),
                arrowprops=dict(arrowstyle="->", lw=2.0, color="#E53E3E", ls="--"))
    ax.text(10.45, 7.35, "Evict $O(1)$", ha="center", fontsize=8, fontweight="bold", color="#E53E3E")

    evict_box = FancyBboxPatch((10.8, 6.7), 1.9, 1.0,
                               boxstyle="round,pad=0.08,rounding_size=0.06",
                               facecolor="#FFF5F5", edgecolor="#FEB2B2", linewidth=1.0)
    ax.add_patch(evict_box)
    ax.text(11.75, 7.42, "Oldest Beats", ha="center", fontsize=8.5, fontweight="bold", color="#9B2C2C")
    ax.text(11.75, 7.12, "Age > Capacity", ha="center", fontsize=7.8, color="#742A2A")
    ax.text(11.75, 6.85, "Zero RAM leaks", ha="center", fontsize=7.5, fontstyle="italic", color="#4A5568")

    # Dynamic Time-Window Slices & Formula (Bottom of Panel A)
    # Window brackets
    window_box = FancyBboxPatch((0.7, 5.08), 8.8, 1.22,
                                boxstyle="round,pad=0.08,rounding_size=0.08",
                                facecolor="#F0FFF4", edgecolor="#9AE6B4", linewidth=1.1)
    ax.add_patch(window_box)
    ax.text(0.9, 6.06, "Dynamic Chronological Slicing (Snapshot under threading.Lock):", fontsize=8.8, fontweight="bold", color="#22543D")

    # Three windows visual
    ax.text(1.2, 5.75, "• 15s Window:", fontsize=8.0, fontweight="bold", color="#276749")
    ax.text(2.4, 5.75, "Acute Reactivity [ts >= now - 15s]  (Early stress onset slope)", fontsize=8.0, fontfamily="monospace", color="#2D3748")

    ax.text(1.2, 5.48, "• 30s Window:", fontsize=8.0, fontweight="bold", color="#276749")
    ax.text(2.4, 5.48, "Ultra-Short-Term Vagal Tone [ts >= now - 30s]  (Evaluated vs. Resting Baseline)", fontsize=8.0, fontfamily="monospace", color="#2D3748")

    ax.text(1.2, 5.21, "• 60s Window:", fontsize=8.0, fontweight="bold", color="#276749")
    ax.text(2.4, 5.21, "Sustained Autonomic Baseline [ts >= now - 60s]  (Standard clinical benchmark)", fontsize=8.0, fontfamily="monospace", color="#2D3748")

    # Formula Box on right
    formula_box = FancyBboxPatch((9.7, 5.08), 4.7, 1.22,
                                 boxstyle="round,pad=0.08,rounding_size=0.08",
                                 facecolor="#EBF8FF", edgecolor="#90CDF4", linewidth=1.1)
    ax.add_patch(formula_box)
    ax.text(12.05, 6.06, "Sliding RMSSD Formulation", ha="center", fontsize=8.8, fontweight="bold", color="#2B6CB0")
    ax.text(12.05, 5.62, r"$\mathrm{RMSSD} = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N-1} (RR_{i+1} - RR_i)^2}$",
            ha="center", va="center", fontsize=9.8, color="#1A365D")
    ax.text(12.05, 5.20, "$N$: Count of valid R-R intervals in selected time window", ha="center", fontsize=7.5, color="#4A5568")


    # =========================================================================
    # PANEL B: PRE-TRIGGER VIDEO FRAME ROLLING BUFFER (Bottom Half)
    # =========================================================================
    panel_b_bg = FancyBboxPatch((0.4, 0.35), 14.2, 4.45,
                                boxstyle="round,pad=0.15,rounding_size=0.12",
                                facecolor="#F8FAFC", edgecolor="#CBD5E0", linewidth=1.2)
    ax.add_patch(panel_b_bg)

    # Panel B Header & Subtitle (Raised with generous 0.35 clearance)
    ax.text(0.7, 4.52, "(B) Pre-Trigger Video Frame Rolling Buffer", fontsize=12.5, fontweight="bold", color="#002060")
    ax.text(5.5, 4.52, "[collections.deque(maxlen=150)]", fontsize=10.5, fontfamily="monospace", fontweight="bold", color="#B41414")
    ax.text(0.7, 4.25, "Solves retroactive ground-truth capture: stores exactly 5.0 seconds of unwritten video in RAM at 30 FPS.",
            fontsize=9.2, color="#4A5568")

    # 1. Camera Stream Ingest (Left)
    cam_box = FancyBboxPatch((0.7, 2.30), 2.3, 1.65,
                             boxstyle="round,pad=0.1,rounding_size=0.08",
                             facecolor="#EBF8FF", edgecolor="#90CDF4", linewidth=1.2)
    ax.add_patch(cam_box)
    ax.text(1.85, 3.65, "Webcam Ingest", ha="center", fontsize=10, fontweight="bold", color="#2B6CB0")
    ax.text(1.85, 3.35, "Standard 720p @ 30 FPS", ha="center", fontsize=8.5, color="#2C5282")
    ax.text(1.85, 3.00, "1 frame every 33.3 ms", ha="center", fontsize=8.2, color="#4A5568")
    ax.text(1.85, 2.65, "MediaPipe Landmark Tracking", ha="center", fontsize=7.8, fontstyle="italic", color="#2B6CB0")

    # Arrow Cam -> Pre-Buffer
    ax.annotate("", xy=(3.3, 3.12), xytext=(3.0, 3.12),
                arrowprops=dict(arrowstyle="->", lw=2.0, color="#3182CE"))
    ax.text(3.15, 3.32, "append()", ha="center", fontsize=8, fontfamily="monospace", fontweight="bold", color="#3182CE")

    # 2. Pre-Buffer Deque (Center-Left)
    pre_box = FancyBboxPatch((3.4, 2.15), 4.2, 1.80,
                            boxstyle="round,pad=0.1,rounding_size=0.1",
                            facecolor="#EDF2F7", edgecolor="#4A5568", linewidth=1.2)
    ax.add_patch(pre_box)
    ax.text(5.5, 3.72, "Pre-Buffer: Rolling 150 Frames", ha="center", fontsize=9.2, fontweight="bold", color="#1A202C")
    ax.text(5.5, 3.48, "Window: [ $T_0 - 5.0\\mathrm{s}$ to $T_0$ ] in RAM", ha="center", fontsize=8.2, color="#4A5568")

    # Mini filmstrip frames
    for i in range(5):
        fx = 3.65 + i * 0.72
        fr = FancyBboxPatch((fx, 2.32), 0.58, 0.88,
                            boxstyle="round,pad=0.02,rounding_size=0.03",
                            facecolor="#E2E8F0" if i < 4 else "#FEEBC8",
                            edgecolor="#718096" if i < 4 else "#DD6B20",
                            linewidth=1.0)
        ax.add_patch(fr)
        lbl = f"f_{i*30}" if i < 4 else "f_150"
        ax.text(fx + 0.29, 2.85, lbl, ha="center", fontsize=7, fontfamily="monospace", color="#2D3748")
        ax.text(fx + 0.29, 2.52, f"-{5-i}s", ha="center", fontsize=7.2, fontweight="bold", color="#4A5568" if i < 4 else "#C05621")

    # 3. TRIGGER EVENT (Center)
    trig_box = FancyBboxPatch((7.85, 2.15), 2.3, 1.80,
                             boxstyle="round,pad=0.1,rounding_size=0.08",
                             facecolor="#FFF5F5", edgecolor="#E53E3E", linewidth=1.8)
    ax.add_patch(trig_box)
    ax.text(9.0, 3.72, "OSCILLATION DETECTED", ha="center", fontsize=8.5, fontweight="bold", color="#C53030")
    ax.text(9.0, 3.45, "Timestamp: $T_0$", ha="center", fontsize=9, fontweight="bold", color="#9B2C2C")
    ax.text(9.0, 3.12, "• 4 velocity reversals", ha="center", fontsize=7.8, color="#742A2A")
    ax.text(9.0, 2.88, "• Threshold > 1.0 px", ha="center", fontsize=7.8, color="#742A2A")
    ax.text(9.0, 2.64, "• Reversal span <= 2.0s", ha="center", fontsize=7.8, color="#742A2A")
    ax.text(9.0, 2.38, "• Cooldown >= 6.0s", ha="center", fontsize=7.8, color="#742A2A")

    # 4. Post-Trigger Capture (Center-Right)
    post_box = FancyBboxPatch((10.35, 2.15), 4.1, 1.80,
                              boxstyle="round,pad=0.1,rounding_size=0.1",
                              facecolor="#FEFCBF", edgecolor="#D69E2E", linewidth=1.2)
    ax.add_patch(post_box)
    ax.text(12.4, 3.72, "Post-Buffer: Next 150 Frames", ha="center", fontsize=9.2, fontweight="bold", color="#744210")
    ax.text(12.4, 3.48, "Window: [ $T_0$ to $T_0 + 5.0\\mathrm{s}$ ] Live Capture", ha="center", fontsize=8.2, color="#744210")

    # Mini filmstrip post frames
    for i in range(5):
        fx = 10.55 + i * 0.72
        fr = FancyBboxPatch((fx, 2.32), 0.58, 0.88,
                            boxstyle="round,pad=0.02,rounding_size=0.03",
                            facecolor="#FEF08A" if i > 0 else "#FEEBC8",
                            edgecolor="#CA8A04" if i > 0 else "#DD6B20",
                            linewidth=1.0)
        ax.add_patch(fr)
        lbl = f"f_{150+i*30}"
        ax.text(fx + 0.29, 2.85, lbl, ha="center", fontsize=7, fontfamily="monospace", color="#744210")
        ax.text(fx + 0.29, 2.52, f"+{i+1}s", ha="center", fontsize=7.2, fontweight="bold", color="#854D0E")

    # Connectors to Synthesis Box
    ax.annotate("", xy=(6.5, 1.65), xytext=(5.5, 2.15),
                arrowprops=dict(arrowstyle="->", lw=1.6, color="#4A5568"))
    ax.annotate("", xy=(8.5, 1.65), xytext=(12.4, 2.15),
                arrowprops=dict(arrowstyle="->", lw=1.6, color="#B7791F"))

    # 5. Synthesized Video Clip Output (Bottom Center)
    out_clip = FancyBboxPatch((3.0, 0.55), 9.0, 1.10,
                              boxstyle="round,pad=0.08,rounding_size=0.1",
                              facecolor="#FAF5FF", edgecolor="#B794F4", linewidth=1.4)
    ax.add_patch(out_clip)
    ax.text(7.5, 1.42, "Synthesized 10-Second Ground-Truth Video Clip (300 Frames at 30 FPS)",
            ha="center", fontsize=9.5, fontweight="bold", color="#553C9A")
    ax.text(7.5, 1.12, "[ 150 Pre-Trigger Frames (-5.0s) ]  +  [ 150 Post-Trigger Frames (+5.0s) ] → nod_YYYYMMDD_HHMMSS.mp4",
            ha="center", fontsize=8.6, fontfamily="monospace", color="#6B46C1")
    ax.text(7.5, 0.82, "Enables precise clinical self-validation via validate_clips.py without writing multi-gigabyte continuous video to disk.",
            ha="center", fontsize=8.0, fontstyle="italic", color="#4A5568")

    plt.tight_layout()
    os.makedirs(DIAGRAM_DIR, exist_ok=True)
    output_path = os.path.join(DIAGRAM_DIR, "diagram_rolling_buffers.png")
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"✅ Generated high-resolution publication diagram: {output_path}")

if __name__ == "__main__":
    create_diagram()
