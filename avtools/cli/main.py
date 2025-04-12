#!/usr/bin/env python3
"""
Main command line interface for avtools.
"""

import argparse
import os
import sys
from argparse import SUPPRESS

from avtools import __version__

# Add the wd14-tagger-standalone directory to Python path
# Consider making this configurable or handling dependencies better
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'wd14-tagger-standalone'))
try:
    from tagger.interrogators import interrogators
    INTERROGATOR_CHOICES = list(interrogators.keys())
except ImportError:
    print("Warning: Could not import interrogators from wd14-tagger-standalone. Tagging features may be unavailable.", file=sys.stderr)
    INTERROGATOR_CHOICES = []

def main():
    """Main entry point for the avtools CLI."""
    parser = argparse.ArgumentParser(
        description="Audio and Video Tools for Media Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # Allow global options before the command
        allow_abbrev=False # Prevent issues with abbreviated commands/options
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    # --- Global Arguments ---
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)"
    )
    parser.add_argument(
        "--debug",
        action="store_const", # Use store_const to set log level
        const="DEBUG",
        dest="log_level", # Set log_level if --debug is used
        help="Enable debug logging (shortcut for --log-level DEBUG)"
    )
    parser.add_argument(
        "--progress-bar",
        action="store_true",
        help="Show progress bars where applicable"
    )
    parser.add_argument(
        "--device",
        help="Specify computation device (e.g., 'cpu', 'cuda', 'mps'). Default auto-detect."
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate output, ensuring the output location only contains results from this run."
    )
    # --- End Global Arguments ---

    # Create subparsers for different tool categories
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Command category to run (audio or video)",
        required=True # Make selecting audio or video mandatory
    )

    # =====================================
    #          Audio Commands
    # =====================================
    audio_parser = subparsers.add_parser(
        "audio",
        help="Audio processing tools",
        description="Tools for processing audio files.",
        # Pass global args by default, don't redefine them
        argument_default=SUPPRESS
    )
    audio_subparsers = audio_parser.add_subparsers(
        title="audio commands",
        dest="audio_command",
        help="Audio command to run",
        required=True # Make selecting an audio command mandatory
    )

    # Audio FCPXML command
    fcpxml_parser = audio_subparsers.add_parser(
        "fcpxml",
        help="Convert audio analysis JSON to FCPXML"
        # Inherits global args
    )
    fcpxml_parser.add_argument(
        "json_file", # Keeping specific name for non-shot analysis
        help="Path to the input audio analysis JSON file."
    )
    fcpxml_parser.add_argument(
        "-o", "--output", required=True, # Standard file output
        help="Path for the output FCPXML file."
    )
    # Keep specific options if they don't fit globally
    fcpxml_parser.add_argument(
        "--fps", type=int, default=50,
        help="Frame rate to use for FCPXML timing (default: 50)"
    )

    # Audio activations command
    activations_parser = audio_subparsers.add_parser(
        "activations",
        help="Convert audio activations to MP4 visualization"
        # Inherits global args
    )
    activations_parser.add_argument(
        "json_file", # Keeping specific name
        help="Path to the input audio activations JSON file."
    )
    activations_parser.add_argument(
        "-o", "--output", required=True, # Standard file output
        help="Path for the output MP4 file."
    )

    # =====================================
    #          Video Commands
    # =====================================
    video_parser = subparsers.add_parser(
        "video",
        help="Video processing tools",
        description="Tools for processing video files, shots, and frames.",
        argument_default=SUPPRESS # Inherits global args
    )
    video_subparsers = video_parser.add_subparsers(
        title="video commands",
        dest="video_command",
        help="Video command to run",
        required=True # Make selecting a video command mandatory
    )

    # Video FCPXML command
    video_fcpxml_parser = video_subparsers.add_parser(
        "fcpxml",
        help="Convert video shot detection JSON to FCPXML"
        # Inherits global args
    )
    video_fcpxml_parser.add_argument(
        "shots_file", # Standardized name
        help="Path to the input JSON file with shot data."
    )
    video_fcpxml_parser.add_argument(
        "-v", "--video",
        help="Path to the source video file (optional, used for metadata)."
    )
    video_fcpxml_parser.add_argument(
        "-o", "--output", required=True, # Standard file output
        help="Path for the output FCPXML file."
    )
    # Frame rate group remains specific to this command
    frame_rate_group = video_fcpxml_parser.add_mutually_exclusive_group()
    frame_rate_group.add_argument(
        "--fps", type=float,
        help="Custom frame rate (default: auto-detect or 50)"
    )
    frame_rate_group.add_argument("--ntsc", action="store_true", help="Use NTSC 29.97 fps")
    frame_rate_group.add_argument("--pal", action="store_true", help="Use PAL 25 fps")
    frame_rate_group.add_argument("--film", action="store_true", help="Use Film 23.976 fps")

    # Video detect shots command
    detect_shots_parser = video_subparsers.add_parser(
        "detect-shots",
        help="Detect shots in a video using TransNetV2"
        # Inherits global args (--device, --log-level, etc.)
    )
    detect_shots_parser.add_argument(
        "video_file",
        help="Path to the video file to analyze."
    )
    detect_shots_parser.add_argument(
        "-o", "--output", # Standard file output
        help="Path for the output JSON file (default: <video_name>_shots.json)."
    )
    # Keep specific threshold and batch size
    detect_shots_parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="Detection threshold (default: 0.5)."
    )
    detect_shots_parser.add_argument(
        "--batch-size", type=int, default=8,
        help="Batch size for processing (default: 8)."
    )

    # Video extract shots command
    extract_shots_parser = video_subparsers.add_parser(
        "extract-shots",
        help="Extract shots (as video clips) from a video based on shot data."
        # Inherits global args (--force, --log-level, etc.)
    )
    extract_shots_parser.add_argument(
        "shots_file", # Standardized name
        help="Path to the JSON file with shot data."
    )
    extract_shots_parser.add_argument(
        "video_file",
        help="Path to the source video file."
    )
    extract_shots_parser.add_argument(
        "-o", "--output-dir", required=True, # Standard dir output
        help="Directory to output extracted shot video files."
    )
    extract_shots_parser.add_argument(
        "-m", "--min-prob", type=float, default=0.5,
        help="Minimum probability threshold for shots (default: 0.5)."
    )

    # Video cache frames command (was extract-frames)
    cache_frames_parser = video_subparsers.add_parser(
        "cache-frames", # Renamed
        help="Extract specific frames from shots and store in cache.",
        description="Extracts frames at specified positions (start, middle, end) or frequency (Hz) within detected shots and saves them to a cache directory.",
        argument_default=SUPPRESS # Inherits global args
    )
    cache_frames_parser.add_argument(
        "video_file",
        help="Path to the video file."
    )
    cache_frames_parser.add_argument(
        "shots_file", # Standardized name
        help="Path to the JSON file with shot data."
    )
    cache_frames_parser.add_argument(
        "--cache-dir",
        help="Custom cache directory path (default: ~/.avtools/cache)."
    )
    cache_frames_parser.add_argument(
        "--video-id",
        help="Custom video ID for caching (defaults to hash of video file)."
    )
    cache_frames_parser.add_argument(
        "--positions", default="start,middle,end",
        help="Comma-separated positions to extract (start,middle,end)."
    )
    cache_frames_parser.add_argument(
        "--format", choices=["jpg", "png"], default="jpg",
        help="Image format (jpg, png)."
    )
    cache_frames_parser.add_argument(
        "--quality", type=int, default=95,
        help="Image quality (1-100)."
    )
    cache_frames_parser.add_argument(
        "--hz", type=float,
        help="Frequency of frame extraction in Hz (alternative to --positions)."
    )
    cache_frames_parser.add_argument(
        "--json-output", action="store_true",
        help="Output results summary in JSON format instead of text."
    )

    # Video extract frames to directory command (was extract-all-frames)
    extract_frames_to_dir_parser = video_subparsers.add_parser(
        "extract-frames-to-dir", # Renamed
        help="Extract frames from shots at intervals to a specified directory.",
        description="Extracts frames based on a time interval or frequency (Hz) within detected shots and saves them directly to an output directory.",
        argument_default=SUPPRESS # Inherits global args
    )
    extract_frames_to_dir_parser.add_argument(
        "video_file",
        help="Path to the video file."
    )
    extract_frames_to_dir_parser.add_argument(
        "shots_file", # Standardized name
        help="Path to the JSON file with shot data."
    )
    extract_frames_to_dir_parser.add_argument(
        "-o", "--output-dir", required=True, # Standard dir output
        help="Output directory for extracted frame image files."
    )
    extract_frames_to_dir_parser.add_argument(
        "--min-probability", type=float, default=0.0,
        help="Minimum probability threshold for shots (default: 0.0)."
    )
    # Frame interval options remain specific
    frame_interval_group = extract_frames_to_dir_parser.add_mutually_exclusive_group()
    frame_interval_group.add_argument(
        "--frame-interval", type=float,
        help="Seconds between frames (e.g., 0.5 = one frame every half second)."
    )
    frame_interval_group.add_argument(
        "--hz", type=float,
        help="Frequency of frame extraction in Hz (e.g., 2.0 = 2 frames per second)."
    )
    extract_frames_to_dir_parser.add_argument(
        "--json-output", action="store_true",
        help="Output results summary in JSON format instead of text."
    )

    # Video cache list command
    cache_list_parser = video_subparsers.add_parser(
        "cache-list",
        help="List cached frames.",
        description="Lists videos and frames currently stored in the cache.",
        argument_default=SUPPRESS # Inherits global args
    )
    cache_list_parser.add_argument(
        "--cache-dir",
        help="Specify cache directory (default: ~/.avtools/cache)."
    )
    cache_list_parser.add_argument(
        "--json-output", action="store_true",
        help="Output list in JSON format."
    )

    # Video cache clear command
    cache_clear_parser = video_subparsers.add_parser(
        "cache-clear",
        help="Clear cache contents.",
        description="Removes cached frames. Can filter by age.",
        argument_default=SUPPRESS # Inherits global args
    )
    cache_clear_parser.add_argument(
        "--cache-dir",
        help="Specify cache directory (default: ~/.avtools/cache)."
    )
    cache_clear_parser.add_argument(
        "--older-than", type=int, metavar='DAYS',
        help="Only clear items older than specified number of days."
    )
    cache_clear_parser.add_argument(
        "--json-output", action="store_true",
        help="Output summary in JSON format."
    )

    # Video extract frame tags command
    extract_frame_tags_parser = video_subparsers.add_parser(
        "extract-frame-tags",
        help="Extract tags from frame images using WD14 tagger.",
        description="Analyzes individual frame images (e.g., extracted by cache-frames or extract-frames-to-dir) and saves tags to JSON files.",
        argument_default=SUPPRESS # Inherits global args (--device, --force, etc.)
    )
    extract_frame_tags_parser.add_argument(
        "frames_dir",
        help="Directory containing frame image files (.jpg, .png, etc.)."
    )
    extract_frame_tags_parser.add_argument(
        "-o", "--output-dir", # Standard dir output
        help="Directory to output tag JSON files (default: same as frames_dir)."
    )
    # Keep model-specific args
    extract_frame_tags_parser.add_argument(
        "--model",
        default="wd14-convnextv2.v1", # Example default
        choices=INTERROGATOR_CHOICES,
        help="Tagger model to use (default: wd14-convnextv2.v1)."
    )
    extract_frame_tags_parser.add_argument(
        "--threshold", type=float, default=0.35,
        help="Prediction threshold for tags (default: 0.35)."
    )
    # Note: --cpu is removed, use global --device cpu

    # Video extract shot tags command
    extract_shot_tags_parser = video_subparsers.add_parser(
        "extract-shot-tags",
        help="Aggregate frame tags into shot-level tags.",
        description="Reads frame tag JSON files and aggregates them based on shot boundaries defined in a shots file.",
        argument_default=SUPPRESS # Inherits global args (--force, --log-level, etc.)
    )
    extract_shot_tags_parser.add_argument(
        "shots_file", # Standardized name
        help="Path to the shots detection JSON file."
    )
    extract_shot_tags_parser.add_argument(
        "tags_dir", # Changed name for clarity
        help="Directory containing frame tag JSON files (output from extract-frame-tags)."
    )
    extract_shot_tags_parser.add_argument(
        "-o", "--output-dir", # Standard dir output
        help="Directory to output aggregated shot tag JSON files."
    )
    # Keep specific args
    extract_shot_tags_parser.add_argument(
        "--min-frames", type=int, default=1, # Default to 1 frame
        help="Minimum number of frames a tag must appear in to be included in shot tags (default: 1)."
    )
    # Note: --progress-bar, --force, --debug are global now

    # --- Argument Parsing ---
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr) # Print help to stderr
        sys.exit(0)

    try:
        args = parser.parse_args()
    except Exception as e:
        print(f"Error parsing arguments: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Command Dispatch ---
    exit_code = 1 # Default exit code for failure
    try:
        if args.command == "audio":
            # Dynamically import to avoid loading unused code
            from avtools.cli import audio_commands
            if args.audio_command == "fcpxml":
                exit_code = audio_commands.json_to_fcpxml_main(args)
            elif args.audio_command == "activations":
                exit_code = audio_commands.activations_main(args)
            # Add other audio commands here if needed
            else:
                # This case should be caught by 'required=True' on subparser
                audio_parser.print_help(sys.stderr)

        elif args.command == "video":
            # Dynamically import to avoid loading unused code
            from avtools.cli import (
                extract_frames,  # Specific module for frame/cache ops
                video_commands,
            )

            if args.video_command == "fcpxml":
                exit_code = video_commands.json_to_fcpxml_main(args)
            elif args.video_command == "detect-shots":
                exit_code = video_commands.detect_shots_main(args)
            elif args.video_command == "extract-shots":
                exit_code = video_commands.extract_shots_main(args)
            elif args.video_command == "cache-frames":
                exit_code = extract_frames.main(args) # Maps to the main func in extract_frames.py
            elif args.video_command == "extract-frames-to-dir":
                exit_code = extract_frames.extract_all_frames_main(args) # Maps to the specific func
            elif args.video_command == "cache-list":
                exit_code = extract_frames.cache_list_main(args)
            elif args.video_command == "cache-clear":
                exit_code = extract_frames.cache_clear_main(args)
            elif args.video_command == "extract-frame-tags":
                exit_code = video_commands.extract_frame_tags_main(args)
            elif args.video_command == "extract-shot-tags":
                exit_code = video_commands.extract_shot_tags_main(args)
            # Add other video commands here if needed
            else:
                # This case should be caught by 'required=True' on subparser
                video_parser.print_help(sys.stderr)
        else:
             # This case should be caught by 'required=True' on subparser
            parser.print_help(sys.stderr)

    except ImportError as e:
         print(f"Error importing command module: {e}", file=sys.stderr)
         print("Please ensure all dependencies are installed correctly.", file=sys.stderr)
         exit_code = 1
    except AttributeError as e:
        # Catch cases where args might be missing if parsing logic changes
        print(f"Error accessing expected argument: {e}", file=sys.stderr)
        print("This might indicate an internal CLI definition error.", file=sys.stderr)
        exit_code = 1
    except Exception as e:
        # Catch-all for unexpected errors during command execution
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        # Optionally include traceback if debug/log level allows
        # import traceback
        # if args.log_level == "DEBUG":
        #    traceback.print_exc()
        exit_code = 1

    sys.exit(exit_code if exit_code is not None else 1)


if __name__ == "__main__":
    main()
