"""
Frame extraction module for video shot analysis.
"""

import json
import os
import sys
import math
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from tqdm import tqdm

import ffmpeg

from .config import get_video_hash, get_video_dir, ensure_cache_dir
from .cache import check_frame_exists, get_frame_path

def extract_frames(
    video_path: Union[str, Path],
    shots_data: Union[str, Path, Dict],
    cache_dir: Optional[Path] = None,
    video_id: Optional[str] = None,
    extract_positions: List[str] = None,
    format_: str = "jpg",
    quality: int = 95
) -> Dict[str, Any]:
    """
    Extract frames from shots in a video and store in cache.
    
    Args:
        video_path: Path to video file
        shots_data: Path to JSON file with shot data or dictionary with shot data
        cache_dir: Optional custom cache directory
        video_id: Optional user-provided video ID (defaults to hash of video file)
        extract_positions: Positions within shots to extract (default: ["start", "middle", "end"])
        format_: Image format (jpg, png)
        quality: Image quality (1-100)
        
    Returns:
        Dict: Extracted frame information
    """
    # Set defaults
    if extract_positions is None:
        extract_positions = ["start", "middle", "end"]
    
    # Convert paths to Path objects
    video_path = Path(video_path)
    
    # Load shot data
    if isinstance(shots_data, (str, Path)):
        shots_data_path = Path(shots_data)
        with open(shots_data_path, 'r') as f:
            shots_data = json.load(f)
    
    # Determine video ID
    if video_id is None:
        video_id = get_video_hash(video_path)
    
    # Ensure cache directory exists
    cache_dir = ensure_cache_dir(cache_dir)
    
    # Ensure video directory exists
    video_dir = get_video_dir(video_id, cache_dir)
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # Get frame rate
    probe = ffmpeg.probe(str(video_path))
    video_stream = next(
        (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
        None
    )
    if not video_stream:
        raise ValueError(f"No video stream found in {video_path}")
    
    # Get frame rate
    if 'avg_frame_rate' in video_stream:
        fps_str = video_stream['avg_frame_rate']
        if '/' in fps_str:
            num, den = map(int, fps_str.split('/'))
            if den == 0:
                fps = 30.0  # Default to 30 fps if division by zero
            else:
                fps = num / den
        else:
            fps = float(fps_str)
    else:
        fps = 30.0  # Default if no frame rate info
    
    # Process shots
    shots = shots_data.get('shots', [])
    if not shots:
        return {
            "success": False,
            "message": "No shots found in data",
            "video_id": video_id
        }
    
    extracted_frames = []
    total_frames = 0
    
    for i, shot in enumerate(shots):
        shot_number = i + 1  # 1-based shot number
        time_offset = float(shot['time_offset'])
        time_duration = float(shot['time_duration'])
        probability = float(shot.get('probability', 1.0))
        
        # Calculate frame positions to extract
        positions = []
        
        if "start" in extract_positions:
            positions.append(("start", time_offset))
        
        if "middle" in extract_positions:
            middle_time = time_offset + (time_duration / 2)
            positions.append(("middle", middle_time))
        
        if "end" in extract_positions:
            end_time = time_offset + time_duration - (1/fps)  # One frame before end
            positions.append(("end", end_time))
        
        # Estimate frame numbers
        shot_frames = []
        
        for position_name, position_time in positions:
            # Estimate frame number based on fps
            frame_number = int(position_time * fps)
            
            # Check if frame already exists in cache
            if check_frame_exists(video_id, frame_number, shot_number, cache_dir):
                frame_path = get_frame_path(video_id, frame_number, shot_number, cache_dir)
                shot_frames.append({
                    "position": position_name,
                    "frame_number": frame_number,
                    "shot_number": shot_number,
                    "time": position_time,
                    "path": str(frame_path),
                    "extracted": False,  # Already existed
                })
                continue
            
            # Extract frame
            output_path = get_frame_path(video_id, frame_number, shot_number, cache_dir)
            
            # Use ffmpeg to extract frame
            try:
                (
                    ffmpeg
                    .input(str(video_path), ss=position_time)
                    .filter('scale', 'iw', 'ih')  # Maintain original size
                    .output(str(output_path), vframes=1, q=quality, format=format_)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                shot_frames.append({
                    "position": position_name,
                    "frame_number": frame_number,
                    "shot_number": shot_number,
                    "time": position_time,
                    "path": str(output_path),
                    "extracted": True,
                })
                total_frames += 1
                
            except ffmpeg.Error as e:
                print(f"Error extracting frame at {position_time}s: {e.stderr.decode() if e.stderr else str(e)}")
            except Exception as e:
                print(f"Unexpected error during frame extraction: {e}")
        
        if shot_frames:
            extracted_frames.append({
                "shot_number": shot_number,
                "time_offset": time_offset,
                "time_duration": time_duration,
                "probability": probability,
                "frames": shot_frames
            })
    
    return {
        "success": True,
        "video_id": video_id,
        "video_path": str(video_path),
        "fps": fps,
        "shots_processed": len(extracted_frames),
        "frames_extracted": total_frames,
        "cache_dir": str(cache_dir),
        "shots": extracted_frames
    }

def extract_all_frames(
    video_path: Union[str, Path],
    shots_data: Union[str, Path, Dict],
    output_dir: Union[str, Path],
    min_probability: float = 0.5,
    frame_interval: Optional[float] = None
) -> Dict[str, Any]:
    """
    Extract all frames from shots at a specified interval and save to directory.
    Uses a single ffmpeg call to extract frames, then renames them based on shot info.
    
    Args:
        video_path: Path to video file
        shots_data: Path to JSON file with shot data or dictionary with shot data
        output_dir: Directory to save frames
        min_probability: Minimum probability threshold for shots
        frame_interval: Seconds between frames (if None, extract every frame)
        
    Returns:
        Dict: Extraction results
    """
    # Convert paths to Path objects
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    
    # Load shot data
    if isinstance(shots_data, (str, Path)):
        shots_data_path = Path(shots_data)
        with open(shots_data_path, 'r') as f:
            shots_data = json.load(f)
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get frame rate
    probe = ffmpeg.probe(str(video_path))
    video_stream = next(
        (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
        None
    )
    if not video_stream:
        raise ValueError(f"No video stream found in {video_path}")
    
    # Get frame rate
    if 'avg_frame_rate' in video_stream:
        fps_str = video_stream['avg_frame_rate']
        if '/' in fps_str:
            num, den = map(int, fps_str.split('/'))
            if den == 0:
                fps = 30.0  # Default to 30 fps if division by zero
            else:
                fps = num / den
        else:
            fps = float(fps_str)
    else:
        fps = 30.0  # Default if no frame rate info
    
    # Determine frame extraction interval
    if frame_interval is None:
        # Extract every frame based on fps
        frame_interval = 1.0 / fps
    
    # Process shots
    shots = shots_data.get('shots', [])
    if not shots:
        return {
            "success": False,
            "message": "No shots found in data"
        }
    
    # Filter shots by probability and calculate total duration
    filtered_shots = []
    total_duration = 0
    for i, shot in enumerate(shots):
        probability = float(shot.get('probability', 1.0))
        if probability >= min_probability:
            shot_info = {
                "shot_number": i + 1,
                "time_offset": float(shot['time_offset']),
                "time_duration": float(shot['time_duration']),
                "probability": probability,
                "start_frame": int(shot['time_offset'] * fps),
                "end_frame": int((shot['time_offset'] + shot['time_duration']) * fps)
            }
            filtered_shots.append(shot_info)
            total_duration += shot_info['time_duration']
    
    if not filtered_shots:
        return {
            "success": False,
            "message": "No shots found above minimum probability threshold"
        }
    
    # Calculate total frames for progress tracking
    total_frames_estimate = int(total_duration * fps)
    
    # Create temporary directory for initial frame extraction
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Extract all frames in one ffmpeg call
        try:
            # Build complex filter to select frames from shots
            filter_parts = []
            for shot in filtered_shots:
                # Convert time range to frame range
                start_frame = shot['start_frame']
                end_frame = shot['end_frame']
                # Add filter to select frames in this range
                filter_parts.append(f"between(n,{start_frame},{end_frame})")
            
            frame_filter = "+".join(filter_parts)
            
            print("Extracting frames with ffmpeg...")
            (
                ffmpeg
                .input(str(video_path))
                .filter('select', frame_filter)
                .filter('scale', 'iw', 'ih')  # Maintain original size
                .output(str(temp_dir / 'frame%06d.jpg'), start_number=0)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Move and rename files based on frame numbers
            print("\nProcessing extracted frames...")
            extracted_frames = []
            
            # List all extracted files
            temp_files = sorted(temp_dir.glob('frame*.jpg'))
            
            with tqdm(total=len(temp_files), desc="Processing frames", unit="frame") as pbar:
                for temp_file in temp_files:
                    # Get frame number from filename
                    frame_num = int(temp_file.stem.replace('frame', ''))
                    
                    # Find which shot this frame belongs to
                    for shot in filtered_shots:
                        if shot['start_frame'] <= frame_num <= shot['end_frame']:
                            # Calculate relative frame position
                            rel_frame = frame_num - shot['start_frame']
                            
                            # Create final filename with both frame number and shot number
                            final_path = output_dir / f"frame{frame_num:06d}_shot{shot['shot_number']:04d}.jpg"
                            
                            # Move file to final location
                            temp_file.rename(final_path)
                            
                            # Record frame info
                            frame_info = {
                                "frame_number": frame_num,
                                "shot_number": shot['shot_number'],
                                "time": frame_num / fps,
                                "path": str(final_path)
                            }
                            extracted_frames.append(frame_info)
                            break
                    
                    pbar.update(1)
            
            # Group frames by shot
            shots_info = []
            for shot in filtered_shots:
                shot_frames = [f for f in extracted_frames if f['shot_number'] == shot['shot_number']]
                if shot_frames:
                    shots_info.append({
                        "shot_number": shot['shot_number'],
                        "time_offset": shot['time_offset'],
                        "time_duration": shot['time_duration'],
                        "probability": shot['probability'],
                        "frames_count": len(shot_frames),
                        "frames": shot_frames
                    })
            
            return {
                "success": True,
                "video_path": str(video_path),
                "fps": fps,
                "shots_processed": len(shots_info),
                "frames_extracted": len(extracted_frames),
                "output_dir": str(output_dir),
                "shots": shots_info
            }
            
        except ffmpeg.Error as e:
            return {
                "success": False,
                "message": f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error during frame extraction: {str(e)}"
            } 