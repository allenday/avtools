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
        
        # Run TransNetV2 prediction
        try:
            predictions = predict_video(
                video_path=str(video_path),
                batch_size=batch_size
            )
        except Exception as e:
            return {
                "success": False,
                "message": f"TransNetV2 prediction failed: {str(e)}"
            }
        
        # Get scene transitions above threshold
        scene_transitions = predictions["scene_transitions"]
        frame_scores = predictions["frame_scores"]
        fps = predictions["fps"]
        
        # Convert transitions to shots
        shots = []
        for i in range(len(scene_transitions) - 1):
            start_frame = scene_transitions[i]
            end_frame = scene_transitions[i + 1]
            
            # Calculate time values
            time_offset = start_frame / fps
            time_duration = (end_frame - start_frame) / fps
            
            # Calculate probability as average of frame scores in shot
            shot_scores = frame_scores[start_frame:end_frame]
            probability = float(np.mean(shot_scores))
            
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
            "total_frames": len(frame_scores),
            "duration": len(frame_scores) / fps,
            "shots": shots
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Shot detection failed: {str(e)}"
        } 