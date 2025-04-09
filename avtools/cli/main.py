#!/usr/bin/env python3
"""
Main command line interface for avtools.
"""

import sys
import argparse
from avtools import __version__

def main():
    """Main entry point for the avtools CLI."""
    parser = argparse.ArgumentParser(
        description="Audio and Video Tools for Media Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    # Create subparsers for different tool categories
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Command to run"
    )
    
    # Audio commands
    audio_parser = subparsers.add_parser(
        "audio",
        help="Audio processing tools"
    )
    audio_subparsers = audio_parser.add_subparsers(
        title="audio commands",
        dest="audio_command",
        help="Audio command to run"
    )
    
    # Audio FCPXML command
    fcpxml_parser = audio_subparsers.add_parser(
        "fcpxml",
        help="Convert audio analysis JSON to FCPXML"
    )
    fcpxml_parser.add_argument(
        "json_file",
        help="Path to the input JSON file."
    )
    fcpxml_parser.add_argument(
        "-o", "--output",
        help="Path for the output FCPXML file."
    )
    fcpxml_parser.add_argument(
        "--fps", type=int, default=50,
        help="Frame rate to use (default: 50)"
    )
    
    # Audio activations command
    activations_parser = audio_subparsers.add_parser(
        "activations",
        help="Convert audio activations to MP4"
    )
    activations_parser.add_argument(
        "json_file",
        help="Path to the input JSON file."
    )
    activations_parser.add_argument(
        "-o", "--output",
        help="Path for the output MP4 file."
    )
    
    # Video commands
    video_parser = subparsers.add_parser(
        "video",
        help="Video processing tools"
    )
    video_subparsers = video_parser.add_subparsers(
        title="video commands",
        dest="video_command",
        help="Video command to run"
    )
    
    # Video FCPXML command
    video_fcpxml_parser = video_subparsers.add_parser(
        "fcpxml",
        help="Convert video shot detection JSON to FCPXML"
    )
    video_fcpxml_parser.add_argument(
        "json_file",
        help="Path to the input JSON file with shot data."
    )
    video_fcpxml_parser.add_argument(
        "-v", "--video",
        help="Path to the source video file (optional)."
    )
    video_fcpxml_parser.add_argument(
        "-o", "--output",
        help="Path for the output FCPXML file."
    )
    
    # Frame rate argument with common presets
    frame_rate_group = video_fcpxml_parser.add_mutually_exclusive_group()
    frame_rate_group.add_argument(
        "--fps", type=float,
        help="Custom frame rate to use (default: auto-detect or 50)"
    )
    frame_rate_group.add_argument(
        "--ntsc", action="store_true",
        help="Use NTSC 29.97 fps"
    )
    frame_rate_group.add_argument(
        "--pal", action="store_true",
        help="Use PAL 25 fps"
    )
    frame_rate_group.add_argument(
        "--film", action="store_true",
        help="Use Film 23.976 fps"
    )
    
    # Video detect shots command
    detect_shots_parser = video_subparsers.add_parser(
        "detect-shots",
        help="Detect shots in a video using TransNetV2"
    )
    detect_shots_parser.add_argument(
        "video_file",
        help="Path to the video file to analyze"
    )
    detect_shots_parser.add_argument(
        "-o", "--output",
        help="Path for the output JSON file (default: <video_name>_shots.json)"
    )
    detect_shots_parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="Detection threshold (default: 0.5)"
    )
    detect_shots_parser.add_argument(
        "--batch-size", type=int, default=8,
        help="Batch size for processing (default: 8)"
    )
    
    # Video extract shots command (renamed from extract)
    extract_shots_parser = video_subparsers.add_parser(
        "extract-shots",
        help="Extract shots from a video based on JSON data"
    )
    extract_shots_parser.add_argument(
        "json_file",
        help="Path to the JSON file with shot data"
    )
    extract_shots_parser.add_argument(
        "video_file",
        help="Path to the video file"
    )
    extract_shots_parser.add_argument(
        "-o", "--output_dir",
        help="Directory to output extracted shots"
    )
    extract_shots_parser.add_argument(
        "-m", "--min_prob", type=float, default=0.5,
        help="Minimum probability threshold for shots (default: 0.5)"
    )
    
    # New command: Video extract frames command
    extract_frames_parser = video_subparsers.add_parser(
        "extract-frames",
        help="Extract frames from shots and store in cache"
    )
    extract_frames_parser.add_argument(
        "video_file",
        help="Path to the video file."
    )
    extract_frames_parser.add_argument(
        "json_file",
        help="Path to the JSON file with shot data."
    )
    extract_frames_parser.add_argument(
        "--cache-dir", 
        help="Custom cache directory path (default: ~/.avtools/cache)"
    )
    extract_frames_parser.add_argument(
        "--video-id",
        help="Custom video ID (defaults to hash of video file)"
    )
    extract_frames_parser.add_argument(
        "--positions", default="start,middle,end",
        help="Comma-separated positions to extract (start,middle,end)"
    )
    extract_frames_parser.add_argument(
        "--format", choices=["jpg", "png"], default="jpg",
        help="Image format (jpg, png)"
    )
    extract_frames_parser.add_argument(
        "--quality", type=int, default=95,
        help="Image quality (1-100)"
    )
    extract_frames_parser.add_argument(
        "--json-output", action="store_true",
        help="Output results in JSON format"
    )
    
    # New command: Extract all frames
    extract_all_frames_parser = video_subparsers.add_parser(
        "extract-all-frames",
        help="Extract all frames from shots at specific intervals"
    )
    extract_all_frames_parser.add_argument(
        "video_file",
        help="Path to the video file."
    )
    extract_all_frames_parser.add_argument(
        "json_file",
        help="Path to the JSON file with shot data."
    )
    extract_all_frames_parser.add_argument(
        "--output-dir", required=True,
        help="Output directory for batch extraction"
    )
    extract_all_frames_parser.add_argument(
        "--min-probability", type=float, default=0.5,
        help="Minimum probability threshold for shots"
    )
    extract_all_frames_parser.add_argument(
        "--frame-interval", type=float,
        help="Seconds between frames (if not specified, extract every frame)"
    )
    extract_all_frames_parser.add_argument(
        "--json-output", action="store_true",
        help="Output results in JSON format"
    )
    
    # New command: Cache list command
    cache_list_parser = video_subparsers.add_parser(
        "cache-list",
        help="List cached frames"
    )
    cache_list_parser.add_argument(
        "--cache-dir",
        help="Custom cache directory path (default: ~/.avtools/cache)"
    )
    cache_list_parser.add_argument(
        "--json-output", action="store_true",
        help="Output results in JSON format"
    )
    
    # New command: Cache clear command
    cache_clear_parser = video_subparsers.add_parser(
        "cache-clear",
        help="Clear cache contents"
    )
    cache_clear_parser.add_argument(
        "--cache-dir",
        help="Custom cache directory path (default: ~/.avtools/cache)"
    )
    cache_clear_parser.add_argument(
        "--older-than", type=int,
        help="Only clear items older than specified days"
    )
    cache_clear_parser.add_argument(
        "--json-output", action="store_true",
        help="Output results in JSON format"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle no arguments case
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
        
    # Import appropriate modules and run commands
    if args.command == "audio":
        if args.audio_command == "fcpxml":
            from avtools.cli.audio_commands import json_to_fcpxml_main
            return json_to_fcpxml_main(args)
        elif args.audio_command == "activations":
            from avtools.cli.audio_commands import activations_to_mp4_main
            return activations_to_mp4_main(args)
        else:
            audio_parser.print_help()
            
    elif args.command == "video":
        if args.video_command == "fcpxml":
            from avtools.cli.video_commands import json_to_fcpxml_main
            return json_to_fcpxml_main(args)
        elif args.video_command == "detect-shots":
            from avtools.cli.video_commands import detect_shots_main
            return detect_shots_main(args)
        elif args.video_command == "extract-shots":
            from avtools.cli.video_commands import extract_shots_main
            return extract_shots_main(args)
        elif args.video_command == "extract-frames":
            from avtools.cli.extract_frames import main as extract_frames_main
            return extract_frames_main(args)
        elif args.video_command == "extract-all-frames":
            from avtools.cli.extract_frames import extract_all_frames_main
            return extract_all_frames_main(args)
        elif args.video_command == "cache-list":
            from avtools.cli.extract_frames import cache_list_main
            return cache_list_main(args)
        elif args.video_command == "cache-clear":
            from avtools.cli.extract_frames import cache_clear_main
            return cache_clear_main(args)
        else:
            video_parser.print_help()
    else:
        parser.print_help()

    return 0

if __name__ == "__main__":
    sys.exit(main()) 