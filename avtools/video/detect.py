"""
Shot detection using TransNetV2.
"""

import sys
import torch
import numpy as np
from pathlib import Path
from typing import Dict, List, Union, Any

from transnetv2_wrapper import predict_video


def detect_shots(
    video_path: Union[str, Path],
    threshold: float = 0.5,
    batch_size: int = 8
) -> Dict[str, Any]:
    """
    Detect shots in a video using TransNetV2.
    
    Args:
        video_path: Path to video file
        threshold: Detection threshold (default: 0.5)
        batch_size: Batch size for processing (default: 8)
        
    Returns:
        Dict containing:
        - success: bool indicating success/failure
        - shots: List of shots with time_offset, time_duration, probability
        - message: Error message if failed
    """
    try:
        video_path = Path(video_path)
        if not video_path.exists():
            return {
                "success": False,
                "message": f"Video file not found: {video_path}"
            }
        
        # Run TransNetV2 prediction with probabilities
        try:
            # Get scene transitions with probabilities
            transitions = predict_video(str(video_path), threshold=threshold, probs=True)
            
            # Get video info for fps
            import ffmpeg
            probe = ffmpeg.probe(str(video_path))
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            fps_str = video_info['r_frame_rate']
            num, den = map(int, fps_str.split('/'))
            fps = num / den if den != 0 else 30.0  # Default to 30fps if division by zero
            
        except Exception as e:
            return {
                "success": False,
                "message": f"TransNetV2 prediction failed: {str(e)}"
            }
        
        # Convert transitions to shots
        shots = []
        for start_frame, end_frame, prob in transitions:
            # Calculate time values
            time_offset = float(start_frame) / fps
            time_duration = float(end_frame - start_frame) / fps
            probability = float(prob)
            
            # Only include shots above threshold
            if probability >= threshold:
                shots.append({
                    "time_offset": time_offset,
                    "time_duration": time_duration,
                    "probability": probability,
                    "start_frame": int(start_frame),
                    "end_frame": int(end_frame)
                })
        
        return {
            "success": True,
            "video_path": str(video_path),
            "fps": fps,
            "threshold": threshold,
            "total_frames": int(transitions[-1][1]) if len(transitions) > 0 else 0,
            "duration": float(transitions[-1][1]) / fps if len(transitions) > 0 else 0,
            "shots": shots
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Shot detection failed: {str(e)}"
        } 