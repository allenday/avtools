"""
CLI command for extracting frames from video shots.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional

from ..video.frames import extract_frames, extract_all_frames
from ..video.cache import get_cache_info, clear_cache


def parse_args():
    """Parse command-line arguments for frame extraction."""
    parser = argparse.ArgumentParser(description="Extract frames from video shots")
    
    # Required arguments
    parser.add_argument("video_path", type=str, help="Path to the video file")
    parser.add_argument("shots_data", type=str, help="Path to the JSON file with shot data")
    
    # Optional arguments
    parser.add_argument("--cache-dir", type=str, help="Custom cache directory path")
    parser.add_argument("--video-id", type=str, help="Custom video ID (defaults to hash of video file)")
    
    # Frame extraction options
    frame_group = parser.add_argument_group("Frame extraction options")
    frame_group.add_argument("--positions", type=str, default="start,middle,end",
                           help="Comma-separated positions to extract (start,middle,end)")
    frame_group.add_argument("--format", type=str, choices=["jpg", "png"], default="jpg",
                           help="Image format (jpg, png)")
    frame_group.add_argument("--quality", type=int, default=95,
                           help="Image quality (1-100)")
    
    # Batch extraction mode
    batch_group = parser.add_argument_group("Batch extraction mode")
    batch_group.add_argument("--extract-all", action="store_true", 
                           help="Extract all frames from shots at specific intervals")
    batch_group.add_argument("--output-dir", type=str,
                           help="Output directory for batch extraction (required with --extract-all)")
    batch_group.add_argument("--min-probability", type=float, default=0.5,
                           help="Minimum probability threshold for shots")
    batch_group.add_argument("--frame-interval", type=float, 
                           help="Seconds between frames (if not specified, extract every frame)")
    
    # Output options
    parser.add_argument("--json-output", action="store_true", 
                      help="Output results in JSON format")
    
    return parser.parse_args()


def main(args=None):
    """Main entry point for frame extraction CLI.
    
    When used directly, parse arguments. When called from avtools main CLI, use passed args.
    """
    # If not called from main CLI, parse args
    if args is None:
        args = parse_args()
    
    # Extract video_path and shots_data from args
    if hasattr(args, 'video_path'):
        video_path = Path(args.video_path)
    else:
        video_path = Path(args.video_file)
    
    if hasattr(args, 'shots_data'):
        shots_data = Path(args.shots_data)
    else:
        shots_data = Path(args.json_file)
    
    # Validate inputs
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        return 1
    
    if not shots_data.exists():
        print(f"Error: Shots data file not found: {shots_data}")
        return 1
    
    # Convert cache_dir to Path if provided
    cache_dir = Path(args.cache_dir) if hasattr(args, 'cache_dir') and args.cache_dir else None
    
    # If extract_all mode (when run from command line)
    if hasattr(args, 'extract_all') and args.extract_all:
        if not args.output_dir:
            print("Error: --output-dir is required with --extract-all")
            return 1
        
        output_dir = Path(args.output_dir)
        
        # Run extraction for all frames
        result = extract_all_frames(
            video_path=video_path,
            shots_data=shots_data,
            output_dir=output_dir,
            min_probability=args.min_probability,
            frame_interval=args.frame_interval
        )
    # If extract_all_frames command (when called from main CLI)
    elif hasattr(args, 'output_dir') and args.output_dir:
        output_dir = Path(args.output_dir)
        min_probability = args.min_probability if hasattr(args, 'min_probability') else 0.5
        frame_interval = args.frame_interval if hasattr(args, 'frame_interval') else None
        
        # Run extraction for all frames
        result = extract_all_frames(
            video_path=video_path,
            shots_data=shots_data,
            output_dir=output_dir,
            min_probability=min_probability,
            frame_interval=frame_interval
        )
    else:
        # Normal extraction mode
        # Parse positions
        if hasattr(args, 'positions'):
            if isinstance(args.positions, str):
                extract_positions = [pos.strip() for pos in args.positions.split(",")]
            else:
                extract_positions = args.positions
        else:
            extract_positions = ["start", "middle", "end"]
        
        # Get format and quality
        format_ = args.format if hasattr(args, 'format') else "jpg"
        quality = args.quality if hasattr(args, 'quality') else 95
        video_id = args.video_id if hasattr(args, 'video_id') else None
        
        # Run extraction
        result = extract_frames(
            video_path=video_path,
            shots_data=shots_data,
            cache_dir=cache_dir,
            video_id=video_id,
            extract_positions=extract_positions,
            format_=format_,
            quality=quality
        )
    
    # Output results
    should_json_output = hasattr(args, 'json_output') and args.json_output
    if should_json_output:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"Successfully processed {result['shots_processed']} shots")
            print(f"Extracted {result['frames_extracted']} frames")
            print(f"Video ID: {result.get('video_id', '')}")
            
            if 'output_dir' in result:
                print(f"Frames saved to: {result['output_dir']}")
            else:
                print(f"Frames saved to cache: {result['cache_dir']}")
        else:
            print(f"Error: {result.get('message', 'Unknown error')}")
    
    return 0 if result["success"] else 1


def extract_all_frames_main(args=None):
    """CLI entry point for extracting all frames."""
    if args is None:
        parser = argparse.ArgumentParser(description="Extract all frames from shots at specific intervals")
        parser.add_argument("video_file", help="Path to the video file")
        parser.add_argument("json_file", help="Path to the JSON file with shot data")
        parser.add_argument("--output-dir", required=True, help="Output directory for batch extraction")
        parser.add_argument("--min-probability", type=float, default=0.5, 
                          help="Minimum probability threshold for shots")
        parser.add_argument("--frame-interval", type=float, 
                          help="Seconds between frames (if not specified, extract every frame)")
        parser.add_argument("--json-output", action="store_true", help="Output results in JSON format")
        args = parser.parse_args()
    
    video_path = Path(args.video_file)
    shots_data = Path(args.json_file)
    output_dir = Path(args.output_dir)
    
    # Validate inputs
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        return 1
    
    if not shots_data.exists():
        print(f"Error: Shots data file not found: {shots_data}")
        return 1
    
    # Run extraction
    result = extract_all_frames(
        video_path=video_path,
        shots_data=shots_data,
        output_dir=output_dir,
        min_probability=args.min_probability,
        frame_interval=args.frame_interval
    )
    
    # Output results
    if hasattr(args, 'json_output') and args.json_output:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"Successfully processed {result['shots_processed']} shots")
            print(f"Extracted {result['frames_extracted']} frames")
            print(f"Frames saved to: {result['output_dir']}")
        else:
            print(f"Error: {result.get('message', 'Unknown error')}")
    
    return 0 if result["success"] else 1


def cache_list_main(args=None):
    """CLI entry point for listing cache contents."""
    if args is None:
        parser = argparse.ArgumentParser(description="List cached frames")
        parser.add_argument("--cache-dir", help="Custom cache directory path")
        parser.add_argument("--json-output", action="store_true", help="Output results in JSON format")
        args = parser.parse_args()
    
    # Get cache dir
    cache_dir = Path(args.cache_dir) if hasattr(args, 'cache_dir') and args.cache_dir else None
    
    # Get cache info
    result = get_cache_info(cache_dir)
    
    # Output results
    if hasattr(args, 'json_output') and args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"Cache directory: {result['cache_dir']}")
        if result["exists"]:
            print(f"Videos: {result['videos']}")
            print(f"Frames: {result['frames']}")
            print(f"Cache size: {result.get('size_mb', 0)} MB")
            
            if result["videos"] > 0:
                print("\nCached videos:")
                for video in result["videos_list"]:
                    print(f"  - {video['video_id']}: {video['frame_count']} frames, "
                          f"{video['shot_count']} shots, {video.get('size_bytes', 0) / (1024*1024):.2f} MB")
        else:
            print("Cache does not exist or is empty")
    
    return 0


def cache_clear_main(args=None):
    """CLI entry point for clearing cache."""
    if args is None:
        parser = argparse.ArgumentParser(description="Clear cache contents")
        parser.add_argument("--cache-dir", help="Custom cache directory path")
        parser.add_argument("--older-than", type=int, help="Only clear items older than specified days")
        parser.add_argument("--json-output", action="store_true", help="Output results in JSON format")
        args = parser.parse_args()
    
    # Get cache dir
    cache_dir = Path(args.cache_dir) if hasattr(args, 'cache_dir') and args.cache_dir else None
    older_than = args.older_than if hasattr(args, 'older_than') else None
    
    # Get cache info before clearing
    before = get_cache_info(cache_dir)
    
    # Clear cache
    result = clear_cache(cache_dir, older_than)
    
    # Output results
    if hasattr(args, 'json_output') and args.json_output:
        print(json.dumps(result, indent=2))
    else:
        if result["cleared"]:
            print(f"Cache cleared successfully")
            print(f"Videos removed: {result['videos_removed']}")
            print(f"Frames removed: {result['frames_removed']}")
            
            if before["exists"]:
                print(f"Space freed: {before.get('size_mb', 0)} MB")
        else:
            print(f"Cache not cleared: {result.get('message', 'Unknown error')}")
    
    return 0


if __name__ == "__main__":
    exit(main()) 