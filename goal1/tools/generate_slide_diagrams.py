import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
GOAL1_DIR = os.path.dirname(TOOLS_DIR)
DIAGRAM_DIR = os.path.join(GOAL1_DIR, "results", "diagrams")

# Set styling
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.family'] = 'sans-serif'

def generate_stress_diagram():
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8F9FA')

    # Title
    ax.text(0.5, 0.95, "How We Tracked Stress: Heart Rate Variability (HRV / RMSSD)", 
            fontsize=14, fontweight='bold', color='#002060', ha='center', va='top', transform=ax.transAxes)
    ax.text(0.5, 0.88, "ECG R-Peak to R-Peak Intervals Measured with 1 ms Medical Precision via Polar H9 Chest Strap", 
            fontsize=9.5, color='#4A5568', ha='center', va='top', transform=ax.transAxes)

    # Left Panel: CALM STATE (High Variability)
    rect_calm = patches.FancyBboxPatch((0.05, 0.12), 0.42, 0.68, boxstyle="round,pad=0.03", 
                                       linewidth=1.5, edgecolor='#228B22', facecolor='#F0FFF4')
    ax.add_patch(rect_calm)

    ax.text(0.26, 0.75, "CALM STATE (High HRV / High RMSSD)", fontsize=11, fontweight='bold', color='#228B22', ha='center')
    ax.text(0.26, 0.70, "Vagus Nerve Active (Parasympathetic Brake ON)", fontsize=9, color='#2D3748', ha='center')

    # Draw simulated ECG with varying intervals
    t_calm = np.linspace(0, 4, 400)
    # peaks at t = 0.5, 1.4 (900ms), 2.15 (750ms), 3.05 (900ms)
    peaks_calm = [0.5, 1.4, 2.15, 3.05]
    intervals_calm = ["900 ms", "750 ms", "900 ms"]
    
    # Plot baseline line
    y_base = 0.45
    ax.plot([0.08, 0.44], [y_base, y_base], color='#A0AEC0', lw=1.2, linestyle=':')

    for p in peaks_calm:
        x_p = 0.08 + (p / 4.0) * 0.36
        # QRS spike
        ax.plot([x_p - 0.015, x_p, x_p + 0.015], [y_base, y_base + 0.12, y_base - 0.03], color='#228B22', lw=2)
        ax.plot([x_p + 0.015, x_p + 0.03], [y_base - 0.03, y_base], color='#228B22', lw=2)

    # Brackets showing varying intervals
    for i in range(len(intervals_calm)):
        x1 = 0.08 + (peaks_calm[i] / 4.0) * 0.36
        x2 = 0.08 + (peaks_calm[i+1] / 4.0) * 0.36
        ax.annotate('', xy=(x2, y_base + 0.13), xytext=(x1, y_base + 0.13),
                    arrowprops=dict(arrowstyle='<->', color='#228B22', lw=1.2))
        ax.text((x1 + x2)/2, y_base + 0.145, intervals_calm[i], fontsize=8, color='#228B22', ha='center', fontweight='bold')

    ax.text(0.26, 0.28, "Flexible, Adaptable Heart Rhythm\nRMSSD = 43.5 ms (Well Above Baseline)", 
            fontsize=9.5, fontweight='bold', color='#1A202C', ha='center')
    ax.text(0.26, 0.17, "-> Head Nodding is Completely Suppressed", 
            fontsize=9, fontweight='bold', color='#228B22', ha='center')

    # Right Panel: STRESSED STATE (Rigid Metronome)
    rect_stress = patches.FancyBboxPatch((0.53, 0.12), 0.42, 0.68, boxstyle="round,pad=0.03", 
                                         linewidth=1.5, edgecolor='#B41414', facecolor='#FFF5F5')
    ax.add_patch(rect_stress)

    ax.text(0.74, 0.75, "STRESSED STATE (Low HRV / Low RMSSD)", fontsize=11, fontweight='bold', color='#B41414', ha='center')
    ax.text(0.74, 0.70, "Vagus Nerve Withdrawn (Fight-or-Flight Active)", fontsize=9, color='#2D3748', ha='center')

    # Draw simulated ECG with rigid identical intervals
    peaks_stress = [0.4, 1.1, 1.8, 2.5, 3.2] # 700ms equal intervals
    intervals_stress = ["650 ms", "650 ms", "650 ms", "650 ms"]

    ax.plot([0.56, 0.92], [y_base, y_base], color='#A0AEC0', lw=1.2, linestyle=':')

    for p in peaks_stress:
        x_p = 0.56 + (p / 3.6) * 0.36
        ax.plot([x_p - 0.012, x_p, x_p + 0.012], [y_base, y_base + 0.12, y_base - 0.03], color='#B41414', lw=2)
        ax.plot([x_p + 0.012, x_p + 0.024], [y_base - 0.03, y_base], color='#B41414', lw=2)

    for i in range(len(intervals_stress)):
        x1 = 0.56 + (peaks_stress[i] / 3.6) * 0.36
        x2 = 0.56 + (peaks_stress[i+1] / 3.6) * 0.36
        ax.annotate('', xy=(x2, y_base + 0.13), xytext=(x1, y_base + 0.13),
                    arrowprops=dict(arrowstyle='<->', color='#B41414', lw=1.2))
        ax.text((x1 + x2)/2, y_base + 0.145, intervals_stress[i], fontsize=7.5, color='#B41414', ha='center', fontweight='bold')

    ax.text(0.74, 0.28, "Rigid, Monotonous 'Metronome' Rhythm\nRMSSD = 28.1 ms (-35.1% Drop)", 
            fontsize=9.5, fontweight='bold', color='#1A202C', ha='center')
    ax.text(0.74, 0.17, "-> Gated Trigger: Head Nodding Manifests!", 
            fontsize=9, fontweight='bold', color='#B41414', ha='center')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    plt.tight_layout()
    os.makedirs(DIAGRAM_DIR, exist_ok=True)
    output_path = os.path.join(DIAGRAM_DIR, "diagram_how_we_tracked_stress.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated stress diagram: {output_path}")

def generate_oscillation_diagram():
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8F9FA')

    # Title
    ax.text(0.5, 0.95, "How We Tracked Oscillations: Computer Vision & Kinematics", 
            fontsize=14, fontweight='bold', color='#002060', ha='center', va='top', transform=ax.transAxes)
    ax.text(0.5, 0.88, "MediaPipe Nose Tip Tracking (30 FPS) + Velocity Zero-Crossing Detection", 
            fontsize=9.5, color='#4A5568', ha='center', va='top', transform=ax.transAxes)

    # Box 1: Landmark Tracking
    box1 = patches.FancyBboxPatch((0.05, 0.15), 0.26, 0.65, boxstyle="round,pad=0.02", 
                                  linewidth=1.2, edgecolor='#002060', facecolor='#F0F4F8')
    ax.add_patch(box1)
    ax.text(0.18, 0.74, "1. MediaPipe Face Mesh", fontsize=10.5, fontweight='bold', color='#002060', ha='center')
    ax.text(0.18, 0.68, "720p Webcam @ 30 FPS", fontsize=9, color='#4A5568', ha='center')
    
    # Simple face icon representation
    face = patches.Circle((0.18, 0.48), 0.12, linewidth=1.5, edgecolor='#002060', facecolor='#E2E8F0')
    ax.add_patch(face)
    # Nose point #1 highlighted in red
    nose = patches.Circle((0.18, 0.47), 0.022, linewidth=1.5, edgecolor='#B41414', facecolor='#E53E3E')
    ax.add_patch(nose)
    ax.text(0.18, 0.47, " #1", fontsize=8, fontweight='bold', color='white', ha='left', va='center')

    ax.text(0.18, 0.28, "Landmark #1 (Nose Tip)\nSelected as the rigid,\nsymmetric anchor of the head.\nImmune to jaw / talking motion.", 
            fontsize=8.5, color='#1A202C', ha='center')

    # Arrow 1 -> 2
    ax.annotate('', xy=(0.36, 0.47), xytext=(0.32, 0.47),
                arrowprops=dict(arrowstyle='->', color='#002060', lw=2))

    # Box 2: EMA Filter & Velocity Zero-Crossing
    box2 = patches.FancyBboxPatch((0.38, 0.15), 0.57, 0.65, boxstyle="round,pad=0.02", 
                                  linewidth=1.2, edgecolor='#002060', facecolor='#FFFFFF')
    ax.add_patch(box2)
    ax.text(0.665, 0.74, "2. Kinematic Velocity & Reversal Counter", fontsize=11, fontweight='bold', color='#002060', ha='center')
    ax.text(0.665, 0.68, "EMA Smoothing (α = 0.4) + Velocity Sign Inversion: v(t) · v(t-1) < 0", fontsize=8.5, color='#4A5568', ha='center')

    # Draw kinematic sine waveform
    t = np.linspace(0, 2.0, 200)
    # 2 Hz oscillation (4 peaks in 2 seconds)
    x_pos = 0.12 * np.sin(2 * np.pi * 2.0 * t)
    
    t_plot = 0.42 + (t / 2.0) * 0.48
    y_plot = 0.46 + x_pos

    ax.plot(t_plot, y_plot, color='#2B6CB0', lw=2.2, label='Filtered X-Displacement')
    ax.plot([0.42, 0.90], [0.46, 0.46], color='#CBD5E0', linestyle='--', lw=1.2) # zero line

    # Highlight Reversals (peaks and troughs)
    reversals = [0.125, 0.375, 0.625, 0.875] # peaks where velocity changes sign
    labels = ["Rev #1", "Rev #2", "Rev #3", "Rev #4 (TRIGGER!)"]
    colors = ['#D69E2E', '#D69E2E', '#D69E2E', '#E53E3E']

    for i, rev in enumerate(reversals):
        rx = 0.42 + (rev / 2.0) * 0.48
        ry = 0.46 + 0.12 * np.sin(2 * np.pi * 2.0 * rev)
        ax.plot(rx, ry, marker='o', markersize=7, color=colors[i])
        ax.text(rx, ry + (0.045 if ry > 0.46 else -0.055), labels[i], 
                fontsize=8, fontweight='bold', color=colors[i], ha='center')

    # Trigger rule banner
    rect_rule = patches.FancyBboxPatch((0.41, 0.18), 0.51, 0.13, boxstyle="round,pad=0.01", 
                                       facecolor='#FFF5F5', edgecolor='#E53E3E', lw=1)
    ax.add_patch(rect_rule)
    ax.text(0.665, 0.245, "TRIGGER CRITERION MET: ≥ 4 Directional Reversals in ≤ 2.0 Seconds", 
            fontsize=8.5, fontweight='bold', color='#B41414', ha='center')
    ax.text(0.665, 0.20, "Displacement > 1 px • Automatically locks 10s ring buffer (5s pre + 5s post)", 
            fontsize=8, color='#4A5568', ha='center')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    plt.tight_layout()
    os.makedirs(DIAGRAM_DIR, exist_ok=True)
    output_path = os.path.join(DIAGRAM_DIR, "diagram_how_we_tracked_oscillations.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated oscillation diagram: {output_path}")

if __name__ == "__main__":
    generate_stress_diagram()
    generate_oscillation_diagram()
