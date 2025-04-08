"""
Video shot extraction module.
Extracts shots from a video based on shot detection data.
"""

import json
import os
from pathlib import Path
from decimal import Decimal

# Import common utilities
from avtools.common.ffmpeg_utils import extract_frames


def extract_shots(json_path, video_path, output_dir=None, min_probability=0.5):
    """
    Extract shots from a video based on shot detection JSON data.
    
    Parameters:
    - json_path: Path to JSON file with shot data
    - video_path: Path to source video file
    - output_dir: Directory to save extracted shots (default: <video_name>_shots)
    - min_probability: Minimum probability threshold for shots (default: 0.5)
    
    Returns:
    - True on success, False on failure
    """
    # Convert paths to Path objects
    json_path = Path(json_path)
    video_path = Path(video_path)
    
    # Verify files exist
    if not json_path.is_file():
        print(f"Error: JSON file not found: {json_path}")
        return False
    
    if not video_path.is_file():
        print(f"Error: Video file not found: {video_path}")
        return False
    
    # Set output directory
    if output_dir is None:
        output_dir = video_path.parent / f"{video_path.stem}_shots"
    else:
        output_dir = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Load JSON data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False
    
    # Extract shots
    shots = data.get('shots', [])
    if not shots:
        print("Error: No shots found in the JSON data.")
        return False
    
    print(f"Found {len(shots)} shots in JSON data")
    print(f"Using probability threshold: {min_probability}")
    
    # Track extraction results
    successful_extractions = 0
    
    # Process each shot
    for i, shot in enumerate(shots):
        try:
            # Get shot data
            shot_start = float(shot['time_offset'])
            shot_duration = float(shot['time_duration'])
            shot_prob = float(shot.get('probability', 1.0))
            
            # Skip shots below probability threshold
            if shot_prob < min_probability:
                print(f"Skipping shot {i+1} (probability {shot_prob:.2f} below threshold {min_probability})")
                continue
            
            # Set output filename
            output_filename = f"shot_{i+1:04d}_{shot_start:.2f}_{shot_duration:.2f}_{shot_prob:.2f}.mp4"
            output_path = output_dir / output_filename
            
            print(f"Extracting shot {i+1}: {shot_start:.2f}s to {shot_start + shot_duration:.2f}s (prob: {shot_prob:.2f})")
            
            # Extract the shot
            result = extract_frames(
                input_path=video_path,
                output_path=output_path,
                time_offset=shot_start,
                time_duration=shot_duration
            )
            
            if result:
                successful_extractions += 1
                print(f"  Saved to: {output_path}")
            else:
                print(f"  Failed to extract shot {i+1}")
                
        except Exception as e:
            print(f"Error processing shot {i+1}: {e}")
    
    # Print summary
    print(f"\nExtraction complete: {successful_extractions} of {len(shots)} shots extracted")
    if successful_extractions > 0:
        print(f"Shots saved to: {output_dir}")
        return True
    else:
        print("No shots were successfully extracted")
        return False 