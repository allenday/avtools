import argparse
import os
import subprocess

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import hsv_to_rgb
from tqdm import tqdm


def main():
    # Default dimension labels
    DEFAULT_LABELS = ['start', 'end', 'intro', 'outro', 'break', 'bridge', 'inst', 'solo', 'verse', 'chorus']

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Visualize multidimensional time series data.')
    parser.add_argument('--input', '-i', type=str, required=True, help='Path to the input .npz file')
    parser.add_argument('--output', '-o', type=str, default='visualization.mp4', help='Path to the output video file')
    parser.add_argument('--normalize', '-n', choices=['none', 'global', 'per-frame'], default='none',
                       help='Normalization method: none (use raw values), global (across all frames), or per-frame')
    parser.add_argument('--fps', type=int, default=10, help='Frames per second for the output video')
    parser.add_argument('--step', type=int, default=1, help='Process every Nth frame (for faster processing)')
    parser.add_argument('--labels', '-l', type=str, default=None,
                        help='Comma-delimited labels for dimensions')
    parser.add_argument('--viz', '-v', type=str, default='both', choices=['radar', 'bar', 'both'],
                      help='Visualization type: radar plot, bar chart, or both')
    parser.add_argument('--max-value', type=float, default=1.0,
                      help='Maximum value for radar plot axis (default: 1.0)')
    args = parser.parse_args()

    # Parse dimension labels
    if args.labels:
        dimension_labels = [label.strip() for label in args.labels.split(',')]
    else:
        dimension_labels = DEFAULT_LABELS

    # Configuration
    DATA_FILE = args.input
    OUTPUT_VIDEO = args.output
    FRAMES_DIR = 'frames'
    FPS = args.fps
    NORMALIZATION = args.normalize
    STEP = args.step
    VIZ_TYPE = args.viz
    MAX_VALUE = args.max_value

    # Load data
    print(f"Loading data from {DATA_FILE}")
    activ = np.load(DATA_FILE)
    labels = activ['label']

    # Get dimensions
    n_dimensions, n_timesteps = labels.shape
    print(f"Data dimensions: {n_dimensions}×{n_timesteps}")
    print(f"Processing every {STEP} frame(s)")
    print(f"Normalization method: {NORMALIZATION}")

    # Ensure we have labels for all dimensions
    if len(dimension_labels) < n_dimensions:
        print(f"Warning: Only {len(dimension_labels)} labels provided for {n_dimensions} dimensions")
        dimension_labels.extend([f"Dim {i}" for i in range(len(dimension_labels), n_dimensions)])
    elif len(dimension_labels) > n_dimensions:
        print(f"Warning: {len(dimension_labels)} labels provided but only {n_dimensions} dimensions exist")
        dimension_labels = dimension_labels[:n_dimensions]

    print(f"Using labels: {dimension_labels}")

    # Create frames directory
    os.makedirs(FRAMES_DIR, exist_ok=True)

    # Calculate global normalization values if needed
    if NORMALIZATION == 'global':
        print("Computing global min/max values...")
        global_min = np.min(labels)
        global_max = np.max(labels)
        print(f"Global min: {global_min}, Global max: {global_max}")

    # Precompute angles for radar plot (in radians)
    angles = np.linspace(0, 2*np.pi, n_dimensions, endpoint=False)

    # Precompute colors for each dimension using HSV color wheel
    dimension_colors = []
    for i in range(n_dimensions):
        # Hue is evenly spaced around the color wheel
        hue = i / n_dimensions
        # Full saturation and value for vibrant colors
        hsv_color = np.array([hue, 1.0, 1.0])
        rgb_color = hsv_to_rgb(hsv_color)
        dimension_colors.append(rgb_color)

    # Generate frames
    frame_count = 0
    for t in tqdm(range(0, n_timesteps, STEP), desc="Generating frames"):
        if VIZ_TYPE == 'both':
            fig = plt.figure(figsize=(16, 7))
            ax_radar = fig.add_subplot(121, polar=True)
            ax_bar = fig.add_subplot(122)
        elif VIZ_TYPE == 'radar':
            fig = plt.figure(figsize=(10, 9))
            ax_radar = fig.add_subplot(111, polar=True)
        else:  # bar only
            fig = plt.figure(figsize=(12, 6))
            ax_bar = fig.add_subplot(111)

        # Current values for this timestep
        values = labels[:, t]

        # Apply normalization if needed
        if NORMALIZATION == 'none':
            # Use raw values
            displayed_values = values.copy()
        elif NORMALIZATION == 'global':
            # Normalize using global min/max
            displayed_values = (values - global_min) / (global_max - global_min)
        else:  # per-frame normalization
            # Normalize using this frame's min/max
            frame_min = np.min(values)
            frame_max = np.max(values)
            if frame_max > frame_min:
                displayed_values = (values - frame_min) / (frame_max - frame_min)
            else:
                displayed_values = np.ones_like(values) * 0.5

        # Calculate the weighted color based on values
        # (Use raw values for color weighting to be data-faithful)
        weighted_color = np.zeros(3)
        total_weight = sum(values)

        if total_weight > 0:  # Avoid division by zero
            for i, val in enumerate(values):
                weighted_color += val * np.array(dimension_colors[i])
            weighted_color /= total_weight

        # Draw radar plot if requested
        if VIZ_TYPE in ['radar', 'both']:
            # Configure radar plot
            ax_radar.set_theta_zero_location("N")  # 0 degrees at top
            ax_radar.set_theta_direction(-1)  # clockwise

            # LAYER 1: Draw color wedges as triangles
            for i in range(n_dimensions):
                # Get angle for this dimension
                angle = angles[i]

                # Create vertices for a triangle from center to unit circle edge
                theta1 = angle - (np.pi / n_dimensions)
                theta2 = angle + (np.pi / n_dimensions)

                # Draw triangle
                ax_radar.fill(
                    [theta1, 0, theta2],  # Fixed order: theta1, center, theta2
                    [1, 0, 1],            # Fixed heights: edge, center, edge
                    color=dimension_colors[i],
                    alpha=0.3,
                    zorder=1
                )

            # LAYER 2: Draw axes and labels in black
            ax_radar.set_xticks(angles)
            ax_radar.set_xticklabels(dimension_labels, fontsize=9)
            ax_radar.set_ylim(0, MAX_VALUE)
            ax_radar.set_rticks([0.25*MAX_VALUE, 0.5*MAX_VALUE, 0.75*MAX_VALUE, MAX_VALUE])
            ax_radar.grid(True, color='black', alpha=0.3, zorder=2)

            # Set aspect to be equal (helps with circle rendering)
            ax_radar.set_aspect('equal')

            # Add title
            if VIZ_TYPE == 'radar':
                title = f'Frame {t+1}/{n_timesteps}'
                if NORMALIZATION != 'none':
                    title += f' ({NORMALIZATION} normalization)'
                ax_radar.set_title(title, y=1.05, fontsize=12)

            # LAYER 3: Add center circle with blended color
            # Create the circle using theta, r coordinates for polar plot
            circle_theta = np.linspace(0, 2*np.pi, 100)
            circle_r = np.ones_like(circle_theta) * 0.25 * MAX_VALUE
            ax_radar.fill(circle_theta, circle_r, color=weighted_color, zorder=3)

            # LAYER 4: Draw radar polyline connecting the data points
            # Create closed loop for polygon by appending first value at end
            angles_closed = np.append(angles, angles[0])
            values_closed = np.append(displayed_values, displayed_values[0])

            # Draw the data polygon
            ax_radar.plot(angles_closed, values_closed, 'k-', linewidth=2, zorder=4)

        # Draw bar chart if requested
        if VIZ_TYPE in ['bar', 'both']:
            if VIZ_TYPE == 'both':
                title = 'Values'
                if NORMALIZATION != 'none':
                    title += f' ({NORMALIZATION} normalization)'
            else:
                title = f'Frame {t+1}/{n_timesteps}'
                if NORMALIZATION != 'none':
                    title += f' ({NORMALIZATION} normalization)'

            ax_bar.set_title(title)

            # Create horizontal bars
            for d in range(n_dimensions):
                # Create the bar with its corresponding color
                ax_bar.barh(d, displayed_values[d], color=dimension_colors[d])

                # Add dimension label and value
                ax_bar.text(-0.05, d, dimension_labels[d], ha='right', va='center',
                           fontweight='bold', fontsize=9)

                # Show the raw value for clarity
                ax_bar.text(displayed_values[d] + 0.02, d, f"{values[d]:.6f}", va='center', fontsize=8)

            # Configure bar chart
            ax_bar.set_xlim(0, MAX_VALUE * 1.1)
            ax_bar.set_ylim(-0.5, n_dimensions - 0.5)
            ax_bar.set_yticks([])  # Hide y-ticks
            ax_bar.set_xlabel('Value')
            ax_bar.grid(axis='x', linestyle='--', alpha=0.4)

        plt.tight_layout()
        plt.savefig(f'{FRAMES_DIR}/frame_{frame_count:05d}.png', dpi=120)
        plt.close()

        frame_count += 1

    # Create video with ffmpeg
    print("Generating video...")
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-framerate', str(FPS),
        '-i', f'{FRAMES_DIR}/frame_%05d.png',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-r', str(FPS),
        OUTPUT_VIDEO
    ]
    subprocess.run(ffmpeg_cmd)

    print(f"Video created: {OUTPUT_VIDEO}")

if __name__ == "__main__":
    main()
