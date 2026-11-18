"""
Analysis & Session Timeline Plotting Script
===========================================
Generates publication-quality session stress timelines (Graph 1) and
statistical summaries comparing physiological state (HRV / RMSSD_30s)
during head oscillation events vs. calibrated resting baselines.

Features:
- Multi-session aware: Plots individual timeline figures per session.
- Filters True Positives (TP): Displays only verified head oscillation events.
- Visualizes Calibrated Baseline: Plots session-specific resting benchmark.
- Saves 300 DPI publication-ready PNG figures.

Usage:
    python analyze_results.py
    python analyze_results.py --session SESS_YYYYMMDD_HHMMSS
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

GOAL1_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_DATA_DIR = os.path.join(GOAL1_DIR, "private_data")
LOG_FILE = os.path.join(PRIVATE_DATA_DIR, "oscillation_log.csv")
DEFAULT_OUTPUT_DIR = os.path.join(GOAL1_DIR, "results", "graphs")


def plot_session_timeline(session_id, session_df, window=30, output_dir="."):
    """
    Generate Graph 1: The Session Stress Timeline.
    Plots continuous RMSSD (30s or 60s) over time, marks the calibrated baseline,
    and highlights verified True Positive (TP) head oscillation events.
    """
    col_name = f"RMSSD_{window}s"
    if col_name not in session_df.columns:
        print(f"  [WARN] Column {col_name} not found in log for session {session_id}. Skipping.")
        return

    # Ensure timestamps are parsed
    session_df = session_df.copy()
    session_df["DT"] = pd.to_datetime(session_df["Timestamp"])
    session_df = session_df.sort_values("DT")

    start_time = session_df["DT"].iloc[0]
    session_df["Elapsed_Min"] = (session_df["DT"] - start_time).dt.total_seconds() / 60.0

    # 1. Identify Calibrated Baseline
    calib_rows = session_df[session_df["Event_Type"] == "CALIB"]
    if not calib_rows.empty and calib_rows[col_name].iloc[0] > 0:
        baseline_rmssd = float(calib_rows[col_name].iloc[0])
        baseline_bpm = float(calib_rows["BPM"].iloc[0])
    else:
        # Fallback to mean of early samples if no explicit CALIB row
        early_samples = session_df[session_df["Elapsed_Min"] <= 2.5]
        baseline_rmssd = float(early_samples[col_name].mean()) if not early_samples.empty else float(session_df[col_name].mean())
        baseline_bpm = float(early_samples["BPM"].mean()) if not early_samples.empty else float(session_df["BPM"].mean())

    # 2. Continuous Timeline Curve
    # Connects all chronological measurements (CALIB, TRACK, BG, and verified TP OSC)
    # ensuring the continuous curve passes directly through verified oscillation events
    timeline_df = session_df[
        session_df["Event_Type"].isin(["CALIB", "TRACK", "BG"]) |
        ((session_df["Event_Type"] == "OSC") & (session_df["Validation_Status"] == "TP"))
    ].sort_values("Elapsed_Min").copy()

    # 3. Oscillation Events
    osc_df = session_df[session_df["Event_Type"] == "OSC"].copy()
    tp_df = osc_df[osc_df["Validation_Status"] == "TP"].copy()
    fp_df = osc_df[osc_df["Validation_Status"] == "FP"].copy()
    unreviewed_df = osc_df[osc_df["Validation_Status"].isna() | (osc_df["Validation_Status"] == "")].copy()

    # Set up matplotlib figure
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax1 = plt.subplots(figsize=(12, 6), dpi=300)

    line_color = "#1f77b4" if window == 30 else "#008080"
    marker_style = "o" if window == 30 else "s"

    # Plot continuous stress curve passing through all timeline points
    if not timeline_df.empty:
        ax1.plot(
            timeline_df["Elapsed_Min"],
            timeline_df[col_name],
            color=line_color,
            linewidth=2.2,
            marker=marker_style,
            markersize=3.5,
            alpha=0.85,
            label=f"Ambient Stress Level ({col_name.replace('_', ' ')})",
            zorder=3
        )

        # Subtle fill indicating parasympathetic withdrawal below baseline
        ax1.fill_between(
            timeline_df["Elapsed_Min"],
            timeline_df[col_name],
            baseline_rmssd,
            where=(timeline_df[col_name] < baseline_rmssd),
            color="#ff9999",
            alpha=0.25,
            interpolate=True,
            label="Vagal Withdrawal (Stress Zone)"
        )

    # Plot horizontal Calibrated Baseline
    ax1.axhline(
        y=baseline_rmssd,
        color="#2ca02c",
        linestyle="--",
        linewidth=2.0,
        alpha=0.9,
        label=f"Calibrated Baseline ({baseline_rmssd:.1f} ms | HR: {baseline_bpm:.0f} bpm)",
        zorder=2
    )

    # Plot TRUE POSITIVE (TP) Oscillation Markers ONLY (coinciding with the line)
    if not tp_df.empty:
        ax1.scatter(
            tp_df["Elapsed_Min"],
            tp_df[col_name],
            color="#d62728",
            edgecolors="black",
            s=130,
            linewidth=1.8,
            zorder=6,
            label=f"True Head Oscillation (TP, n={len(tp_df)})"
        )

        # Annotate each True Positive with a staggered callout label
        for idx, (_, row) in enumerate(tp_df.iterrows(), start=1):
            delta = ((row[col_name] - baseline_rmssd) / baseline_rmssd) * 100
            y_offset = -28 if (idx % 2 == 1) else -42
            ax1.annotate(
                f"Nod #{idx}\n{row[col_name]:.1f}ms ({delta:+.0f}%)",
                xy=(row["Elapsed_Min"], row[col_name]),
                xytext=(0, y_offset),
                textcoords="offset points",
                ha="center",
                fontsize=8.5,
                fontweight="bold",
                color="#990000",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#fff0f0", edgecolor="#d62728", alpha=0.9),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.0", color="#d62728", lw=1.2)
            )

    # Titles and Labels
    window_desc = "Ultra-Short-Term (30s)" if window == 30 else "Short-Term Sustained (60s)"
    ax1.set_title(
        f"Session Stress Timeline ({window_desc}) — Head Oscillations vs. Calibrated Baseline\nSession: {session_id}",
        fontsize=13,
        fontweight="bold",
        pad=14
    )
    ax1.set_xlabel("Elapsed Time (Minutes into Session)", fontsize=11, fontweight="bold")
    ax1.set_ylabel(f"Parasympathetic Vagal Tone: {col_name.replace('_', ' ')} (ms)\n[Lower Value = Higher Stress]", fontsize=11, fontweight="bold")

    # Set reasonable Y-axis bounds
    all_rmssd = session_df[col_name].dropna()
    min_y = max(0, all_rmssd.min() - 8) if not all_rmssd.empty else 0
    max_y = max(baseline_rmssd + 15, all_rmssd.max() + 10) if not all_rmssd.empty else 80
    ax1.set_ylim(min_y, max_y)

    # Grid & Legend
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", frameon=True, framealpha=0.95, facecolor="white", edgecolor="#cccccc", fontsize=9.5)

    plt.tight_layout()
    output_filename = os.path.join(output_dir, f"session_{session_id}_timeline_{window}s.png")
    fig.savefig(output_filename, dpi=300)
    plt.close(fig)

    print(f"  [PLOT] Generated {window}s timeline plot: {output_filename}")
    if not unreviewed_df.empty:
        print(f"     [WARN] Note: {len(unreviewed_df)} unreviewed clip(s) in this session. "
              f"Run 'python validate_clips.py' to verify them so they appear as TP.")
    if not fp_df.empty:
        print(f"     [INFO] Filtered: {len(fp_df)} False Positive(s) excluded from graph.")


def plot_dual_timeline(session_id, session_df, output_dir="."):
    """
    Generate Dual Comparative Graph: Stacked 30s vs 60s RMSSD.
    Panel A: 30s Ultra-Short-Term Reactivity
    Panel B: 60s Sustained Vagal Tone
    """
    session_df = session_df.copy()
    session_df["DT"] = pd.to_datetime(session_df["Timestamp"])
    session_df = session_df.sort_values("DT")

    start_time = session_df["DT"].iloc[0]
    session_df["Elapsed_Min"] = (session_df["DT"] - start_time).dt.total_seconds() / 60.0

    calib_rows = session_df[session_df["Event_Type"] == "CALIB"]
    base_30 = float(calib_rows["RMSSD_30s"].iloc[0]) if not calib_rows.empty and calib_rows["RMSSD_30s"].iloc[0] > 0 else float(session_df["RMSSD_30s"].mean())
    base_60 = float(calib_rows["RMSSD_60s"].iloc[0]) if not calib_rows.empty and calib_rows["RMSSD_60s"].iloc[0] > 0 else float(session_df["RMSSD_60s"].mean())
    base_bpm = float(calib_rows["BPM"].iloc[0]) if not calib_rows.empty else float(session_df["BPM"].mean())

    track_df = session_df[session_df["Event_Type"].isin(["CALIB", "TRACK", "BG"])].copy()
    tp_df = session_df[(session_df["Event_Type"] == "OSC") & (session_df["Validation_Status"] == "TP")].copy()

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), dpi=300, sharex=True)

    # --- TOP PANEL: 30s RMSSD ---
    if not track_df.empty:
        ax1.plot(track_df["Elapsed_Min"], track_df["RMSSD_30s"], color="#1f77b4", lw=2.0, marker="o", ms=3.5, label="Ambient RMSSD 30s")
        ax1.fill_between(track_df["Elapsed_Min"], track_df["RMSSD_30s"], base_30, where=(track_df["RMSSD_30s"] < base_30), color="#ff9999", alpha=0.25, interpolate=True)
    ax1.axhline(base_30, color="#2ca02c", ls="--", lw=1.8, label=f"Calibrated Baseline ({base_30:.1f} ms | HR: {base_bpm:.0f} bpm)")
    if not tp_df.empty:
        ax1.scatter(tp_df["Elapsed_Min"], tp_df["RMSSD_30s"], color="#d62728", edgecolors="black", s=120, lw=1.5, zorder=6, label=f"Head Nodding (TP, n={len(tp_df)})")
        for idx, (_, row) in enumerate(tp_df.iterrows(), start=1):
            delta = ((row["RMSSD_30s"] - base_30) / base_30) * 100
            ax1.annotate(f"Nod #{idx}: {row['RMSSD_30s']:.1f}ms ({delta:+.0f}%)", xy=(row["Elapsed_Min"], row["RMSSD_30s"]), xytext=(0, 15), textcoords="offset points", ha="center", fontsize=8, fontweight="bold", color="#990000", bbox=dict(boxstyle="round,pad=0.2", facecolor="#fff0f0", edgecolor="#d62728", alpha=0.9))

    ax1.set_title(f"Comparative Multiscale Autonomic Stress Analysis — Session: {session_id}\nPanel A: Ultra-Short-Term RMSSD (30-Second Window)", fontsize=11, fontweight="bold", loc="left")
    ax1.set_ylabel("RMSSD 30s (ms)", fontsize=10, fontweight="bold")
    ax1.legend(loc="upper right", frameon=True, fontsize=8.5)
    ax1.grid(True, ls=":", alpha=0.6)

    # --- BOTTOM PANEL: 60s RMSSD ---
    if not track_df.empty:
        ax2.plot(track_df["Elapsed_Min"], track_df["RMSSD_60s"], color="#008080", lw=2.0, marker="s", ms=3.5, label="Ambient RMSSD 60s")
        ax2.fill_between(track_df["Elapsed_Min"], track_df["RMSSD_60s"], base_60, where=(track_df["RMSSD_60s"] < base_60), color="#b0e0e6", alpha=0.3, interpolate=True)
    ax2.axhline(base_60, color="#2ca02c", ls="--", lw=1.8, label=f"Calibrated Baseline ({base_60:.1f} ms)")
    if not tp_df.empty:
        ax2.scatter(tp_df["Elapsed_Min"], tp_df["RMSSD_60s"], color="#d62728", edgecolors="black", s=120, lw=1.5, zorder=6, label=f"Head Nodding (TP, n={len(tp_df)})")
        for idx, (_, row) in enumerate(tp_df.iterrows(), start=1):
            delta = ((row["RMSSD_60s"] - base_60) / base_60) * 100
            ax2.annotate(f"Nod #{idx}: {row['RMSSD_60s']:.1f}ms ({delta:+.0f}%)", xy=(row["Elapsed_Min"], row["RMSSD_60s"]), xytext=(0, 15), textcoords="offset points", ha="center", fontsize=8, fontweight="bold", color="#990000", bbox=dict(boxstyle="round,pad=0.2", facecolor="#fff0f0", edgecolor="#d62728", alpha=0.9))

    ax2.set_title("Panel B: Short-Term Sustained RMSSD (60-Second Window)", fontsize=11, fontweight="bold", loc="left")
    ax2.set_ylabel("RMSSD 60s (ms)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Elapsed Time (Minutes into Session)", fontsize=10, fontweight="bold")
    ax2.legend(loc="upper right", frameon=True, fontsize=8.5)
    ax2.grid(True, ls=":", alpha=0.6)

    plt.tight_layout()
    output_filename = os.path.join(output_dir, f"session_{session_id}_timeline_dual.png")
    fig.savefig(output_filename, dpi=300)
    plt.close(fig)
    print(f"  [PLOT] Generated dual comparative plot: {output_filename}")


def main():
    parser = argparse.ArgumentParser(description="Analyze nystagmus stress correlation dataset.")
    parser.add_argument("--session", type=str, default=None, help="Specific Session_ID to analyze/plot.")
    parser.add_argument("--log", "-l", type=str, default=LOG_FILE,
                        help=f"Path to CSV log file (default: {LOG_FILE})")
    parser.add_argument("--output-dir", "-o", type=str, default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory for generated graphs (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--window", "-w", type=str, default="30", choices=["30", "60", "both"],
                        help="RMSSD window duration to plot: '30', '60', or 'both' (default: '30')")
    parser.add_argument("--dual", action="store_true",
                        help="Optionally generate stacked dual 30s/60s comparative plot (default: False)")
    parser.add_argument("--stats", action="store_true",
                        help="Optionally print dataset-wide Mann-Whitney hypothesis tests (default: False)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if not os.path.exists(args.log):
        print(f"[ERROR] Log file {args.log} not found.")
        sys.exit(1)

    df = pd.read_csv(args.log)
    if df.empty or len(df) == 0:
        print(f"[INFO] {LOG_FILE} is empty. Run OscillationTracker.py to collect your first session.")
        sys.exit(0)

    # Ensure Session_ID column exists
    if "Session_ID" not in df.columns:
        df["Session_ID"] = "LEGACY_SESSION"

    # Fill NaN strings
    df["Validation_Status"] = df["Validation_Status"].fillna("").astype(str)
    df["Event_Type"] = df["Event_Type"].fillna("").astype(str)

    unique_sessions = df["Session_ID"].unique()

    print("\n" + "=" * 70)
    print("      NYSTAGMUS STRESS CORRELATION — MULTI-SESSION SUMMARY")
    print("=" * 70)
    print(f" Total Logged Records:       {len(df)}")
    print(f" Total Sessions Recorded:    {len(unique_sessions)}")

    for sess in unique_sessions:
        s_df = df[df["Session_ID"] == sess]
        calib = s_df[s_df["Event_Type"] == "CALIB"]
        tp = s_df[s_df["Validation_Status"] == "TP"]
        fp = s_df[s_df["Validation_Status"] == "FP"]
        unreviewed = s_df[(s_df["Event_Type"] == "OSC") & (s_df["Validation_Status"] == "")]

        base_str_30 = f"{calib['RMSSD_30s'].iloc[0]:.1f}ms" if not calib.empty and calib['RMSSD_30s'].iloc[0] > 0 else "N/A"
        base_str_60 = f"{calib['RMSSD_60s'].iloc[0]:.1f}ms" if not calib.empty and calib['RMSSD_60s'].iloc[0] > 0 else "N/A"
        base_bpm = f"{calib['BPM'].iloc[0]:.0f}bpm" if not calib.empty else "N/A"

        total_triggers = len(tp) + len(fp)
        prec_str = f" | Precision: {len(tp)/total_triggers*100:.0f}%" if total_triggers > 0 else ""
        print(f"\n  * Session: {sess}")
        print(f"    - Calibrated Baseline: 30s: {base_str_30} | 60s: {base_str_60} | HR: {base_bpm}")
        print(f"    - Oscillation Triggers: {total_triggers + len(unreviewed)} (TP: {len(tp)}, FP: {len(fp)}, Unreviewed: {len(unreviewed)}{prec_str})")

        if not tp.empty and not calib.empty:
            tp_mean_30 = tp["RMSSD_30s"].mean()
            base_val_30 = calib["RMSSD_30s"].iloc[0]
            delta_30 = ((tp_mean_30 - base_val_30) / base_val_30) * 100

            tp_mean_60 = tp["RMSSD_60s"].mean()
            base_val_60 = calib["RMSSD_60s"].iloc[0]
            delta_60 = ((tp_mean_60 - base_val_60) / base_val_60) * 100

            print(f"    - Mean RMSSD_30s during Nodding: {tp_mean_30:.1f} ms ({delta_30:+.1f}% vs. Baseline)")
            print(f"    - Mean RMSSD_60s during Nodding: {tp_mean_60:.1f} ms ({delta_60:+.1f}% vs. Baseline)")

    # Dataset-Wide Precision Summary
    all_tp = df[df["Validation_Status"] == "TP"]
    all_fp = df[df["Validation_Status"] == "FP"]
    if len(all_tp) + len(all_fp) > 0:
        tot = len(all_tp) + len(all_fp)
        prec = (len(all_tp) / tot) * 100
        print("\n" + "-" * 70)
        print(f"      OVERALL DETECTOR PERFORMANCE: {len(all_tp)} TP, {len(all_fp)} FP ({tot} Triggers)")
        print(f"      Detection Precision: {prec:.0f}% ({prec:.1f}%)")
        print("-" * 70)

    # Generate Timeline Plots
    print("\n" + "-" * 70)
    print(f"      GENERATING SESSION TIMELINE GRAPHS (Window Mode: {args.window})")
    print("-" * 70)

    target_sessions = [args.session] if args.session else unique_sessions
    for sess in target_sessions:
        s_df = df[df["Session_ID"] == sess]
        if not s_df.empty:
            if args.window in ["30", "both"]:
                plot_session_timeline(sess, s_df, window=30, output_dir=args.output_dir)
            if args.window in ["60", "both"]:
                plot_session_timeline(sess, s_df, window=60, output_dir=args.output_dir)
            if args.dual:
                plot_dual_timeline(sess, s_df, output_dir=args.output_dir)

    # Dataset-Wide Statistical Comparison (only if --stats is requested)
    if args.stats:
        all_tp = df[df["Validation_Status"] == "TP"]
        all_calib = df[df["Event_Type"].isin(["CALIB", "TRACK", "BG"])]

        if len(all_tp) >= 2 and len(all_calib) >= 2:
            print("\n" + "-" * 70)
            print("      OVERALL STATISTICAL HYPOTHESIS TESTS (ALL SESSIONS)")
            print("-" * 70)

            # 30-Second Test
            u_stat_30, p_val_30 = stats.mannwhitneyu(all_tp["RMSSD_30s"], all_calib["RMSSD_30s"], alternative="less")
            tp_mean_30 = all_tp["RMSSD_30s"].mean()
            calib_mean_30 = all_calib["RMSSD_30s"].mean()
            delta_30 = ((tp_mean_30 - calib_mean_30) / calib_mean_30) * 100

            print(f" [30-Second Window]")
            print(f"   True Positive (TP) Mean RMSSD: {tp_mean_30:.2f} ms")
            print(f"   Baseline / Ambient Mean RMSSD: {calib_mean_30:.2f} ms")
            print(f"   Stress Delta:                  {delta_30:+.1f}%")
            print(f"   Mann-Whitney U Statistic:      {u_stat_30}")
            print(f"   P-Value:                       {p_val_30:.4f}")

            # 60-Second Test
            u_stat_60, p_val_60 = stats.mannwhitneyu(all_tp["RMSSD_60s"], all_calib["RMSSD_60s"], alternative="less")
            tp_mean_60 = all_tp["RMSSD_60s"].mean()
            calib_mean_60 = all_calib["RMSSD_60s"].mean()
            delta_60 = ((tp_mean_60 - calib_mean_60) / calib_mean_60) * 100

            print(f"\n [60-Second Window]")
            print(f"   True Positive (TP) Mean RMSSD: {tp_mean_60:.2f} ms")
            print(f"   Baseline / Ambient Mean RMSSD: {calib_mean_60:.2f} ms")
            print(f"   Stress Delta:                  {delta_60:+.1f}%")
            print(f"   Mann-Whitney U Statistic:      {u_stat_60}")
            print(f"   P-Value:                       {p_val_60:.4f}")

            if p_val_60 < 0.05 or p_val_30 < 0.05:
                print("\n Verdict: Statistically Significant Stress Modulation Detected (p < 0.05)!")
            else:
                print(f"\n Verdict: p = {min(p_val_30, p_val_60):.3f} (Trending towards significance).")

            print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
