import argparse
import json
import os
import ffmpeg
import torch
from transnetv2_wrapper import predict_video

def get_video_fps(video_path):
    """
    Use ffprobe to determine the FPS of a video file.
    Returns the FPS as a float, or None if it couldn't be determined.
    """
    try:
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream:
            # Handle both fraction and decimal format
            fps_str = video_stream.get('r_frame_rate', '')
            if fps_str and '/' in fps_str:
                num, den = map(float, fps_str.split('/'))
                if den != 0:  # Avoid division by zero
                    return num / den
            # Try avg_frame_rate if r_frame_rate isn't available or couldn't be parsed
            fps_str = video_stream.get('avg_frame_rate', '')
            if fps_str and '/' in fps_str:
                num, den = map(float, fps_str.split('/'))
                if den != 0:  # Avoid division by zero
                    return num / den
            # Try tbr as last resort
            tbr = video_stream.get('tbr')
            if tbr:
                return float(tbr)
        return None
    except Exception as e:
        print(f"Warning: Could not determine FPS: {e}")
        return None

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Detect scene transitions in video files')
    parser.add_argument('input_video', help='Path to the input video file')
    parser.add_argument('-o', '--output', help='Path to output JSON file', required=True)
    parser.add_argument('--fps', type=float, help='Frames per second of the video (autodetected if not provided)')
    parser.add_argument('-d', '--device', choices=['cuda', 'cpu'], 
                      help='Device to use for computation (default: cuda if available, else cpu)')
    args = parser.parse_args()
    
    # Ensure input file exists
    if not os.path.exists(args.input_video):
        print(f"Error: Input video file '{args.input_video}' not found")
        return 1
    
    # Get absolute path of input video
    input_video_abs_path = os.path.abspath(args.input_video)
    
    # Auto-detect FPS if not provided
    if args.fps is None:
        detected_fps = get_video_fps(args.input_video)
        if detected_fps:
            args.fps = detected_fps
            print(f"Autodetected FPS: {args.fps}")
        else:
            args.fps = 24.0
            print(f"Could not autodetect FPS, using default: {args.fps}")
    else:
        print(f"Using provided FPS: {args.fps}")
    
    # Determine device
    if args.device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using {'CUDA' if device == 'cuda' else 'CPU'} (auto-detected)")
    else:
        device = args.device
        if device == 'cuda' and not torch.cuda.is_available():
            print("Warning: CUDA requested but not available. Falling back to CPU.")
            device = 'cpu'
        print(f"Using {device.upper()} (user-specified)")
    
    print(f"Processing video: {args.input_video}")
    print(f"Output will be saved to: {args.output}")
    
    # Process the video
    shots = predict_video(args.input_video, probs=True, device=device)
    
    # Prepare results for JSON output
    results = []
    for i, t in enumerate(shots):
        frame_start = t[0]
        frame_end = t[1]
        frame_prob = t[2] if len(t) > 2 else None
        
        time_duration = int(100 * (frame_end - frame_start) / args.fps) / 100
        time_offset = int(100 * frame_start / args.fps) / 100
        
        shot_data = {
            "id": i,
            "frame_start": int(frame_start),
            "frame_end": int(frame_end),
            "time_offset": time_offset,
            "time_duration": time_duration
        }
        
        if frame_prob is not None:
            shot_data["probability"] = float(frame_prob)
            
        results.append(shot_data)
    
    # Save results to JSON file with video path included
    output_data = {
        "path": input_video_abs_path,
        "shots": results
    }
    
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Processed {len(results)} shots. Results saved to {args.output}")
    return 0

if __name__ == "__main__":
    exit(main())
