#!/usr/bin/env python3
"""
Command-line interfaces for video processing tools.
"""

import sys
import argparse
import json
from pathlib import Path

# Import video library functions
from avtools.video import fcpxml
from avtools.video import shots
from avtools.video.detect import detect_shots
from avtools.video.fcpxml import shots_to_fcpxml


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
    result = shots.extract_shots(
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


if __name__ == "__main__":
    # If this script is run directly, determine which function to call
    script_name = Path(sys.argv[0]).name
    
    if "json_to_fcpxml" in script_name:
        sys.exit(json_to_fcpxml_main())
    elif "extract_shots" in script_name:
        sys.exit(extract_shots_main())
    elif "detect_shots" in script_name:
        sys.exit(detect_shots_main(sys.argv[1]))
    else:
        print(f"Error: Unknown script name: {script_name}")
        sys.exit(1) 