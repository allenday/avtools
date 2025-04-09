#!/usr/bin/env python3
"""
Command-line interfaces for video processing tools.
"""

import sys
import os
import argparse
import json
import warnings
from pathlib import Path
from typing import Dict, List
from PIL import Image
from tqdm import tqdm

# Import video library functions
from avtools.video import fcpxml
from avtools.video.detect import detect_shots
from ..video.shots import extract_shots

# Silence ONNX warnings about execution providers
warnings.filterwarnings('ignore', category=UserWarning, module='onnxruntime')

# Add the wd14-tagger-standalone directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'wd14-tagger-standalone'))
from tagger.interrogator import Interrogator
from tagger.interrogators import interrogators


def json_to_fcpxml_main(args=None):
    """CLI entry point for video JSON to FCPXML conversion."""
    if args is None:
        # Create parser for direct script invocation
        parser = argparse.ArgumentParser(
            description='Convert video shot detection JSON to FCPXML v1.13 with frame-aligned markers.'
        )
        parser.add_argument(
            'json_file',
            help='Path to the input JSON file with shot data.'
        )
        parser.add_argument(
            '-v', '--video',
            help='Path to the source video file (optional).'
        )
        parser.add_argument(
            '-o', '--output',
            help='Path for the output FCPXML file.'
        )
        
        # Frame rate argument with common presets
        frame_rate_group = parser.add_mutually_exclusive_group()
        frame_rate_group.add_argument(
            '--fps', type=float,
            help='Custom frame rate to use (default: auto-detect or 50)'
        )
        frame_rate_group.add_argument(
            '--ntsc', action='store_true',
            help='Use NTSC 29.97 fps'
        )
        frame_rate_group.add_argument(
            '--pal', action='store_true',
            help='Use PAL 25 fps'
        )
        frame_rate_group.add_argument(
            '--film', action='store_true',
            help='Use Film 23.976 fps'
        )
        
        args = parser.parse_args()
    
    # Convert paths to Path objects
    input_json_path = Path(args.json_file)
    if not input_json_path.is_file():
        print(f"Error: Input JSON file not found: {input_json_path}")
        return 1
    
    output_fcpxml_path = Path(args.output) if args.output else input_json_path.with_suffix('.fcpxml')
    
    # Determine frame rate from arguments
    frame_rate = None
    if hasattr(args, 'ntsc') and args.ntsc:
        frame_rate = 29.97
    elif hasattr(args, 'pal') and args.pal:
        frame_rate = 25
    elif hasattr(args, 'film') and args.film:
        frame_rate = 23.976
    elif hasattr(args, 'fps') and args.fps:
        frame_rate = args.fps
    
    # Convert video path
    video_path = Path(args.video) if args.video else None
    
    # Call the library function
    result = fcpxml.json_to_fcpxml(
        input_json_path=input_json_path,
        output_fcpxml_path=output_fcpxml_path,
        video_path=video_path,
        frame_rate=frame_rate
    )
    
    return 0 if result else 1


def extract_shots_main(args=None):
    """CLI entry point for extracting shots from a video."""
    if args is None:
        # Create parser for direct script invocation
        parser = argparse.ArgumentParser(
            description='Extract shots from a video based on shot detection JSON.'
        )
        parser.add_argument(
            'json_file',
            help='Path to the JSON file with shot data.'
        )
        parser.add_argument(
            'video_file',
            help='Path to the video file.'
        )
        parser.add_argument(
            '-o', '--output_dir',
            help='Directory to output extracted shots.'
        )
        parser.add_argument(
            '-m', '--min_prob', type=float, default=0.5,
            help='Minimum probability threshold for shots (default: 0.5).'
        )
        
        args = parser.parse_args()
    
    # Convert paths to Path objects
    json_path = Path(args.json_file)
    if not json_path.is_file():
        print(f"Error: Input JSON file not found: {json_path}")
        return 1
    
    video_path = Path(args.video_file)
    if not video_path.is_file():
        print(f"Error: Video file not found: {video_path}")
        return 1
    
    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = video_path.parent / f"{video_path.stem}_shots"
    
    # Call the library function
    result = extract_shots(
        json_path=json_path,
        video_path=video_path,
        output_dir=output_dir,
        min_probability=args.min_prob
    )
    
    return 0 if result else 1


def detect_shots_main(args):
    """
    Main entry point for shot detection command.
    """
    video_path = Path(args.video_file)
    
    # Set default output path if not provided
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = video_path.with_name(f"{video_path.stem}_shots.json")
    
    # Run shot detection
    result = detect_shots(
        video_path=video_path,
        threshold=args.threshold,
        batch_size=args.batch_size
    )
    
    if result["success"]:
        # Write results to JSON file
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Shot detection complete:")
        print(f"- Found {len(result['shots'])} shots")
        print(f"- Results saved to: {output_path}")
        return 0
    else:
        print(f"Error: {result.get('message', 'Shot detection failed')}")
        return 1


def extract_frame_tags_main(args=None):
    """CLI entry point for extracting tags from frame images."""
    if args is None:
        parser = argparse.ArgumentParser(
            description='Extract tags from frame images using WD14 tagger.'
        )
        parser.add_argument(
            'frames_dir',
            help='Directory containing frame images.'
        )
        parser.add_argument(
            '-o', '--output_dir',
            help='Directory to output JSON files (default: same as frames).'
        )
        parser.add_argument(
            '--model',
            default='wd14-convnextv2.v1',
            choices=list(interrogators.keys()),
            help='Model to use for prediction (default: wd14-convnextv2.v1)'
        )
        parser.add_argument(
            '--threshold', type=float, default=0.35,
            help='Prediction threshold (default: 0.35)'
        )
        parser.add_argument(
            '--cpu',
            action='store_true',
            help='Use CPU only'
        )
        parser.add_argument(
            '--progress-bar',
            action='store_true',
            help='Show progress bar'
        )
        args = parser.parse_args()

    frames_dir = Path(args.frames_dir)
    if not frames_dir.is_dir():
        print(f"Error: Frames directory not found: {frames_dir}")
        return 1

    # Use a dedicated output directory by default
    output_dir = Path(args.output_dir) if args.output_dir else frames_dir.parent / 'frame_tags'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize tagger
    interrogator = interrogators[args.model]
    if args.cpu:
        interrogator.use_cpu()

    # Process each frame
    frame_files = sorted(frames_dir.glob('*.jpg'))
    if not frame_files:
        print(f"Error: No jpg files found in {frames_dir}")
        return 1

    # Create progress bar if requested
    if args.progress_bar:
        frame_files = tqdm(frame_files, desc="Processing frames")

    for frame_path in frame_files:
        json_path = output_dir / f"{frame_path.stem}.json"
        
        if json_path.exists():
            if args.progress_bar:
                frame_files.write(f"Skipping existing: {json_path}")
            else:
                print(f"Skipping existing: {json_path}")
            continue

        if not args.progress_bar:
            print(f"Processing: {frame_path}")
            
        try:
            # Get frame tags
            result = interrogator.interrogate(Image.open(frame_path))
            tags = Interrogator.postprocess_tags(
                result[1],
                threshold=args.threshold,
                replace_underscore=True
            )
            
            # Save tags
            with open(json_path, 'w') as f:
                json.dump({
                    'frame': str(frame_path),
                    'tags': tags
                }, f, indent=2)
        except Exception as e:
            msg = f"Error processing {frame_path}: {e}"
            if args.progress_bar:
                frame_files.write(msg)
            else:
                print(msg)
            continue

    return 0


def extract_shot_tags_main(args=None):
    """CLI entry point for aggregating frame tags into shot tags."""
    if args is None:
        parser = argparse.ArgumentParser(
            description='Aggregate frame tags into shot-level tags.'
        )
        parser.add_argument(
            'shots_json',
            help='Path to shots detection JSON file.'
        )
        parser.add_argument(
            'frames_dir',
            help='Directory containing frame tag JSON files.'
        )
        parser.add_argument(
            '-o', '--output_dir',
            help='Directory to output shot tag JSON files.'
        )
        parser.add_argument(
            '--min_frames', type=int, default=2,
            help='Minimum frames required to include a tag (default: 2)'
        )
        parser.add_argument(
            '--progress-bar',
            action='store_true',
            help='Show progress bar'
        )
        args = parser.parse_args()

    # Load shots data
    shots_path = Path(args.shots_json)
    if not shots_path.is_file():
        print(f"Error: Shots JSON not found: {shots_path}")
        return 1

    frames_dir = Path(args.frames_dir)
    if not frames_dir.is_dir():
        print(f"Error: Frames directory not found: {frames_dir}")
        return 1

    # Ensure frame tags exist by running extract_frame_tags if needed
    frame_files = list(frames_dir.glob('*.jpg'))
    json_files = list(frames_dir.glob('*.json'))
    if len(json_files) < len(frame_files):
        print("Some frame tags missing. Running extract_frame_tags first...")
        # Create complete Namespace with all required arguments
        frame_tag_args = argparse.Namespace(
            frames_dir=str(frames_dir),
            output_dir=None,
            model='wd14-convnextv2.v1',
            threshold=0.35,
            cpu=False,
            progress_bar=getattr(args, 'progress_bar', False)  # Get progress_bar from args or default to False
        )
        result = extract_frame_tags_main(frame_tag_args)
        if result != 0:
            return result

    output_dir = Path(args.output_dir) if args.output_dir else shots_path.parent / 'shot_tags'
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(shots_path) as f:
        shots_data = json.load(f)

    # Process each shot
    shots = shots_data['shots']
    if args.progress_bar:
        shots = tqdm(list(enumerate(shots)), desc="Processing shots")
    else:
        shots = enumerate(shots)

    for i, shot in shots:
        shot_json = output_dir / f"shot_{i:04d}.json"
        if shot_json.exists():
            if args.progress_bar:
                shots.write(f"Skipping existing: {shot_json}")
            else:
                print(f"Skipping existing: {shot_json}")
            continue

        if not args.progress_bar:
            print(f"Processing shot {i}")
        
        # Collect frame numbers in this shot
        start_frame = shot['start_frame']
        end_frame = shot['end_frame']
        
        # Aggregate tags from all frames in shot
        tag_counts: Dict[str, int] = {}
        frame_count = 0
        
        for frame_num in range(start_frame, end_frame + 1):
            frame_json = frames_dir / f"frame_{frame_num:06d}.json"
            if not frame_json.exists():
                continue
                
            frame_count += 1
            with open(frame_json) as f:
                frame_data = json.load(f)
                for tag in frame_data['tags']:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Filter tags that appear in minimum number of frames
        shot_tags = {
            tag: count/frame_count 
            for tag, count in tag_counts.items() 
            if count >= args.min_frames
        }

        # Save shot tags
        with open(shot_json, 'w') as f:
            json.dump({
                'shot_index': i,
                'start_frame': start_frame,
                'end_frame': end_frame,
                'frame_count': frame_count,
                'tags': shot_tags
            }, f, indent=2)

    return 0


if __name__ == "__main__":
    # If this script is run directly, determine which function to call
    script_name = Path(sys.argv[0]).name
    
    if "json_to_fcpxml" in script_name:
        sys.exit(json_to_fcpxml_main())
    elif "extract_shots" in script_name:
        sys.exit(extract_shots_main())
    elif "detect_shots" in script_name:
        sys.exit(detect_shots_main(sys.argv[1]))
    elif "extract_frame_tags" in script_name:
        sys.exit(extract_frame_tags_main())
    elif "extract_shot_tags" in script_name:
        sys.exit(extract_shot_tags_main())
    else:
        print(f"Error: Unknown script name: {script_name}")
        sys.exit(1) 