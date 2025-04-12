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
import logging
import subprocess

# Import video library functions
from avtools.video import fcpxml
from avtools.video.detect import detect_shots
from ..video.shots import extract_shots

# Silence ONNX warnings about execution providers
warnings.filterwarnings('ignore', category=UserWarning, module='onnxruntime')

# Add the wd14-tagger-standalone directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'wd14-tagger-standalone'))
from tagger.interrogator.interrogator import AbsInterrogator as Interrogator
from tagger.interrogators import interrogators

# Set up logging with a null handler by default
# Each function will configure its own logger based on CLI args
logging.getLogger('avtools').addHandler(logging.NullHandler())
logger = logging.getLogger('avtools.cli')


def setup_logger(args):
    """Set up logger with proper configuration based on args.
    
    Args:
        args: Argument namespace which may contain debug and progress_bar flags
        
    Returns:
        Configured logger instance
    """
    # Check if debug and progress-bar flags exist in args, default to False if not
    debug = getattr(args, 'debug', False)
    progress_bar = getattr(args, 'progress_bar', False)
    
    # Configure logging based on arguments
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Create a custom handler that respects the progress bar
    class TqdmLoggingHandler(logging.Handler):
        def emit(self, record):
            try:
                msg = self.format(record)
                # Write to tqdm's output if we're using a progress bar
                if progress_bar and hasattr(tqdm, 'write'):
                    tqdm.write(msg)
                else:
                    # Use subprocess.run with cat to avoid pager interactions
                    subprocess.run(["echo", msg, "|", "cat"], shell=True, check=False)
                self.flush()
            except Exception:
                self.handleError(record)
    
    # Set up the handler and formatter
    handler = TqdmLoggingHandler()
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    
    # Configure the logger
    logger = logging.getLogger('avtools.cli')
    logger.setLevel(log_level)
    
    # Remove any existing handlers
    for hdlr in logger.handlers[:]:
        logger.removeHandler(hdlr)
    logger.addHandler(handler)
    
    # Don't propagate to root logger to avoid duplicate messages
    logger.propagate = False
    
    return logger


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
    """
    CLI entry point for extracting tags from frame images.
    
    This function handles flexible argument positioning, allowing options
    to be placed anywhere in the command line.
    
    Args:
        args: Parsed arguments from argparse, or None to parse from sys.argv
        
    Returns:
        int: 0 on success, 1 on failure
    """
    # Create the parser if args not provided
    parser = argparse.ArgumentParser(
        description='Extract tags from frame images using WD14 tagger'
    )
    parser.add_argument(
        'frames_dir',
        help='Directory containing frame images.'
    )
    parser.add_argument(
        '-o', '--output_dir',
        help='Directory to output JSON files (default: same as frames)'
    )
    parser.add_argument(
        '--model',
        default='wd14-convnextv2.v1',
        choices=list(interrogators.keys()),
        help=f'Model to use for prediction (default: wd14-convnextv2.v1)'
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
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing output files'
    )
    
    # Only parse args if they weren't provided
    if args is None:
        args = parser.parse_args()
    
    # Check if we have the required arguments
    required_attrs = ["frames_dir"]
    missing_attrs = [attr for attr in required_attrs if not hasattr(args, attr)]
    
    # If attributes are missing, look for them with different naming
    if missing_attrs:
        # Map between possible attribute names
        attr_map = {
            "frames_dir": ["frames_directory", "frames_path", "img_dir", "image_dir"]
        }
        
        # Try to find missing attributes with alternate names
        for attr in missing_attrs[:]:  # Work on a copy
            for alt_attr in attr_map.get(attr, []):
                if hasattr(args, alt_attr):
                    # Create the required attribute from the alternate
                    setattr(args, attr, getattr(args, alt_attr))
                    missing_attrs.remove(attr)
                    break
    
    # If we still have missing required attributes, print help and exit
    if missing_attrs:
        print(f"Error: Missing required arguments: {', '.join(missing_attrs)}")
        parser.print_help()
        return 1

    # Set up logger
    logger = setup_logger(args)
    
    # Get option values with safe defaults
    frames_dir = Path(args.frames_dir)
    output_dir = Path(args.output_dir) if hasattr(args, 'output_dir') and args.output_dir else frames_dir
    model_name = getattr(args, 'model', 'wd14-convnextv2.v1')
    threshold = getattr(args, 'threshold', 0.35)
    use_cpu = getattr(args, 'cpu', False)
    progress_bar = getattr(args, 'progress_bar', False)
    debug_mode = getattr(args, 'debug', False)
    force = getattr(args, 'force', False)
    
    # Set a quiet mode if progress bar is active and we're not in debug mode
    quiet_mode = progress_bar and not debug_mode
    
    # Helper function for conditional logging
    def log(message, always=False):
        if always or not quiet_mode:
            logger.info(message)
    
    # Check if frames directory exists
    if not frames_dir.is_dir():
        logger.error(f"Error: Frames directory not found: {frames_dir}")
        return 1
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize the tagger
    log("Loading WD14 tagger environment...", always=True)
    
    # Check for environment variables
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    
    # Set device
    device = "cpu" if use_cpu else None
    
    # Initialize tagger and tag expander
    try:
        if model_name in interrogators:
            tagger = interrogators[model_name]
            if tagger is None:
                logger.error(f"Error: Failed to initialize model: {model_name}")
                return 1
        else:
            logger.error(f"Error: Unknown model: {model_name}")
            return 1
        
        # Initialize tag expander
        if debug_mode:
            log("Initializing tag expander...")
        from danbooru_tag_expander import TagExpander
        expander = TagExpander()
        
        if debug_mode:
            log("Tagger and expander initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing tagger: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()
        return 1
    
    # Find image files in frames directory
    log(f"Scanning for images in {frames_dir}...")
    
    image_suffixes = {'.jpg', '.jpeg', '.png', '.webp'}
    image_files = [
        f for f in frames_dir.iterdir()
        if f.is_file() and f.suffix.lower() in image_suffixes
    ]
    
    if not image_files:
        logger.warning(f"No image files found in {frames_dir}")
        return 0
    
    log(f"Found {len(image_files)} image files")
    
    # Setup for processing
    total_processed = 0
    total_skipped = 0
    
    # Process each image
    pbar = None
    if progress_bar:
        pbar = tqdm(sorted(image_files), desc="Processing frames")
        files_iter = pbar
    else:
        files_iter = sorted(image_files)
    
    for img_file in files_iter:
        # Determine output filename
        json_file = output_dir / f"{img_file.stem}.json"
        
        # Skip if already exists and not force
        if json_file.exists() and not force:
            log(f"Skipping existing: {json_file}")
            total_skipped += 1
            continue
        
        try:
            # Load image and get predictions
            img = Image.open(img_file)
            
            # Get predictions
            log(f"Processing {img_file.name}...")
            
            # Get raw ratings and tags with confidence scores
            ratings, raw_tags = tagger.interrogate(img)
            
            # Filter by threshold and get tag names
            selected_tags = [
                tag for tag, score in raw_tags.items()
                if score >= threshold
            ]
            
            # Get expanded tags
            expanded_tags = expander.expand_tags(selected_tags)
            
            # Save results
            with open(json_file, 'w') as f:
                json.dump({
                    'image': str(img_file),
                    'threshold': threshold,
                    'ratings': ratings,
                    'raw_tags': {tag: score for tag, score in raw_tags.items() if score >= threshold},
                    'expanded_tags': expanded_tags
                }, f, indent=2)
            
            total_processed += 1
                
        except Exception as e:
            logger.error(f"Error processing {img_file.name}: {e}")
            if debug_mode:
                import traceback
                traceback.print_exc()
            continue
    
    log(f"Complete: {total_processed} images processed, {total_skipped} skipped. Results saved to {output_dir}", always=True)
    return 0


def extract_shot_tags_main(args=None):
    """
    CLI entry point for aggregating frame tags into shot-level tags.
    
    This function handles flexible argument positioning, so options like
    --min_frames and --output_dir can be placed anywhere in the command line.
    
    Args:
        args: Parsed arguments from argparse, or None to parse from sys.argv
        
    Returns:
        int: 0 on success, 1 on failure
    """
    # Create the parser if args not provided
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
        '--min_frames', type=int, default=0,
        help='Minimum frames required to include a tag (default: 0)'
    )
    parser.add_argument(
        '--progress-bar',
        action='store_true',
        help='Show progress bar'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing output files'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    # Only parse args if they weren't provided
    if args is None:
        args = parser.parse_args()
    
    # Check if we have the required arguments
    required_attrs = ["shots_json", "frames_dir"]
    missing_attrs = [attr for attr in required_attrs if not hasattr(args, attr)]
    
    # If attributes are missing, look for them with different naming
    if missing_attrs:
        # Map between possible attribute names
        attr_map = {
            "shots_json": ["shots_data", "json_file", "json_path"],
            "frames_dir": ["frames_directory", "tags_dir", "frames_path"]
        }
        
        # Try to find missing attributes with alternate names
        for attr in missing_attrs[:]:  # Work on a copy
            for alt_attr in attr_map.get(attr, []):
                if hasattr(args, alt_attr):
                    # Create the required attribute from the alternate
                    setattr(args, attr, getattr(args, alt_attr))
                    missing_attrs.remove(attr)
                    break
    
    # If we still have missing required attributes, print help and exit
    if missing_attrs:
        print(f"Error: Missing required arguments: {', '.join(missing_attrs)}")
        parser.print_help()
        return 1

    # Set up logger
    logger = setup_logger(args)
    
    # Get debug mode and progress bar status safely
    debug_mode = getattr(args, 'debug', False)
    progress_bar = getattr(args, 'progress_bar', False)
    force = getattr(args, 'force', False)
    min_frames = getattr(args, 'min_frames', 0)

    # Load shots data
    shots_path = Path(args.shots_json)
    if not shots_path.is_file():
        logger.error(f"Error: Shots JSON not found: {shots_path}")
        return 1

    frames_dir = Path(args.frames_dir)
    if not frames_dir.is_dir():
        logger.error(f"Error: Frames directory not found: {frames_dir}")
        return 1

    output_dir = Path(args.output_dir) if hasattr(args, 'output_dir') and args.output_dir else shots_path.parent / 'shot_tags'
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(shots_path) as f:
        shots_data = json.load(f)

    # Process each shot
    shots = shots_data['shots']
    pbar = None
    if progress_bar:
        pbar = tqdm(list(enumerate(shots)), desc="Processing shots")
        shots_iter = pbar
    else:
        shots_iter = enumerate(shots)

    total_processed = 0
    total_skipped = 0

    for i, shot in shots_iter:
        shot_json = output_dir / f"shot_{i:04d}.json"
        if shot_json.exists() and not force:
            logger.debug(f"Skipping existing: {shot_json}")
            total_skipped += 1
            continue

        logger.debug(f"Processing shot {i}")
        
        # Find all frame JSON files for this shot using shot number
        frame_pattern = f"tc_*_shot{i:04d}.json"
        frame_files = sorted(frames_dir.glob(frame_pattern))
        
        # If no files found with the new pattern, try the legacy pattern as fallback
        if not frame_files:
            legacy_pattern = f"frame*_shot{i:04d}.json"
            frame_files = sorted(frames_dir.glob(legacy_pattern))
            if frame_files:
                logger.info(f"Found files using legacy pattern {legacy_pattern}")
        
        if not frame_files:
            logger.warning(f"No frame files found for shot {i} using pattern {frame_pattern}")
            continue
            
        # Count tag occurrences across all frames in the shot
        tag_counts = {}
        frame_count = 0
        
        for frame_json in frame_files:
            try:
                with open(frame_json) as f:
                    frame_data = json.load(f)
                    for tag in frame_data.get('tags', []):
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
                frame_count += 1
            except json.JSONDecodeError as e:
                logger.error(f"Error reading JSON from {frame_json}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing {frame_json}: {e}")
                if debug_mode:
                    import traceback
                    traceback.print_exc()
                continue

        if frame_count == 0:
            logger.warning(f"No valid frames processed for shot {i}")
            continue

        # Filter tags by minimum frame threshold
        shot_tags = {
            tag: count
            for tag, count in tag_counts.items()
            if count >= min_frames
        }

        # Save shot tags
        with open(shot_json, 'w') as f:
            json.dump({
                'shot_index': i,
                'start_frame': shot['start_frame'],
                'end_frame': shot['end_frame'],
                'frame_count': frame_count,
                'tags': shot_tags
            }, f, indent=2)
        
        total_processed += 1

    logger.info(f"Complete: {total_processed} shots processed, {total_skipped} skipped. Results saved to {output_dir}")
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