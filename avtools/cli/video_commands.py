#!/usr/bin/env python3
"""
Command-line interfaces for video processing tools.
"""

import json
import logging
import os
import sys
import traceback  # For debug logging
from pathlib import Path

from PIL import Image
from tqdm import tqdm

# Import video library functions
from avtools.video import fcpxml
from avtools.video.detect import (
    detect_shots,  # Assuming detect_shots handles device internally now
)

from ..video.shots import extract_shots

# Silence ONNX warnings about execution providers - Consider making this conditional on log level
# warnings.filterwarnings('ignore', category=UserWarning, module='onnxruntime')

# Add the wd14-tagger-standalone directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'wd14-tagger-standalone'))
try:
    from tagger.interrogator.interrogator import AbsInterrogator as Interrogator
    from tagger.interrogators import interrogators
except ImportError:
    # This case is handled in main.py, but good practice to check here too
    Interrogator = None
    interrogators = {}
    logging.getLogger('avtools.cli').warning("Could not import interrogators from wd14-tagger-standalone.")


# Import tag expander utility
try:
    from danbooru_tag_expander.utils.tag_expander import TagExpander
except ImportError:
    TagExpander = None # Handle gracefully if not installed
    logging.getLogger('avtools.cli').warning("danbooru_tag_expander not found. Tag expansion will be skipped.")


# Set up logging with a null handler by default
# Each function will configure its own logger based on CLI args
logging.getLogger('avtools').addHandler(logging.NullHandler())
# Define logger at module level for convenience
logger = logging.getLogger('avtools.cli')


def setup_logger(args):
    """Set up logger with proper configuration based on global args.

    Args:
        args: Argument namespace containing global args like log_level, progress_bar

    Returns:
        Configured logger instance
    """
    log_level_name = getattr(args, 'log_level', 'INFO') # Default to INFO
    log_level = logging.getLevelName(log_level_name)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    progress_bar = getattr(args, 'progress_bar', False)

    # Use StreamHandler, potentially wrapped by tqdm if progress bar is active
    if progress_bar:
        # Custom handler to integrate with tqdm
        class TqdmLoggingHandler(logging.Handler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                    tqdm.write(msg, file=sys.stderr) # Write to stderr via tqdm
                    self.flush()
                except Exception:
                    self.handleError(record)
        handler = TqdmLoggingHandler()
    else:
        # Standard handler writing to stderr
        handler = logging.StreamHandler(sys.stderr)

    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)

    # Configure the logger instance obtained at module level
    logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicates if called multiple times
    for hdlr in logger.handlers[:]:
        logger.removeHandler(hdlr)
    logger.addHandler(handler)

    # Don't propagate to root logger to avoid duplicate messages
    logger.propagate = False

    logger.debug(f"Logger configured with level: {log_level_name}")
    return logger


def json_to_fcpxml_main(args):
    """CLI entry point for video JSON to FCPXML conversion."""
    logger = setup_logger(args) # Setup logger first

    # Access args directly - parsing done in main.py
    try:
        input_json_path = Path(args.shots_file) # Use standardized name
        if not input_json_path.is_file():
            logger.error(f"Input shots file not found: {input_json_path}")
            return 1

        output_fcpxml_path = Path(args.output) # Use standardized name
        output_fcpxml_path.parent.mkdir(parents=True, exist_ok=True) # Ensure output dir exists

        # Determine frame rate from specific arguments for this command
        frame_rate = None
        if hasattr(args, 'ntsc') and args.ntsc:
            frame_rate = 29.97
        elif hasattr(args, 'pal') and args.pal:
            frame_rate = 25
        elif hasattr(args, 'film') and args.film:
            frame_rate = 23.976
        elif hasattr(args, 'fps') and args.fps:
            frame_rate = args.fps
        logger.debug(f"Using frame rate: {frame_rate if frame_rate else 'Auto/Default'}")

        # Convert video path if provided
        video_path = Path(args.video) if hasattr(args, 'video') and args.video else None
        if video_path and not video_path.is_file():
            logger.warning(f"Optional video file not found: {video_path}")
            video_path = None

        # Call the library function
        logger.info(f"Converting {input_json_path} to FCPXML at {output_fcpxml_path}...")
        result = fcpxml.json_to_fcpxml(
            input_json_path=input_json_path,
            output_fcpxml_path=output_fcpxml_path,
            video_path=video_path,
            frame_rate=frame_rate
        )

        if result:
            logger.info("Conversion successful.")
            return 0
        else:
            logger.error("Conversion failed.")
            return 1

    except AttributeError as e:
        logger.error(f"Missing expected argument: {e}")
        return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if logger.level == logging.DEBUG:
            traceback.print_exc()
        return 1


def extract_shots_main(args):
    """CLI entry point for extracting shots from a video."""
    logger = setup_logger(args)

    try:
        json_path = Path(args.shots_file) # Use standardized name
        if not json_path.is_file():
            logger.error(f"Input shots file not found: {json_path}")
            return 1

        video_path = Path(args.video_file)
        if not video_path.is_file():
            logger.error(f"Video file not found: {video_path}")
            return 1

        # Use standardized output dir arg
        output_dir = Path(args.output_dir)
        # No default here, main.py makes it required

        min_probability = getattr(args, 'min_prob', 0.5) # Keep specific arg

        # Note: Global --force is available in args.force if needed for overwriting checks
        # Renamed: Use args.regenerate
        # regenerate = getattr(args, 'regenerate', False) # Removed unused variable
        # The underlying extract_shots function needs to handle overwriting based on this.
        # Currently, it seems extract_shots doesn't have overwrite protection.

        logger.info(f"Extracting shots from {video_path} based on {json_path}...")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Minimum probability: {min_probability}")

        # Call the library function (assuming it handles logging/progress)
        result = extract_shots(
            json_path=json_path,
            video_path=video_path,
            output_dir=output_dir,
            min_probability=min_probability,
            # Potentially pass args.regenerate here if the function supports it
            # regenerate=regenerate
        )

        if result:
            logger.info("Shot extraction successful.")
            return 0
        else:
            logger.error("Shot extraction failed.")
            return 1

    except AttributeError as e:
        logger.error(f"Missing expected argument: {e}")
        return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if logger.level == logging.DEBUG:
            traceback.print_exc()
        return 1


def detect_shots_main(args):
    """Main entry point for shot detection command."""
    logger = setup_logger(args)

    try:
        video_path = Path(args.video_file)
        if not video_path.is_file():
            logger.error(f"Video file not found: {video_path}")
            return 1

        # Handle default output path if -o is not provided
        if hasattr(args, 'output') and args.output:
             output_path = Path(args.output)
        else:
             output_path = video_path.with_name(f"{video_path.stem}_shots.json")
             logger.info(f"Output path not specified, defaulting to: {output_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Check force flag before running
        # Renamed: Check regenerate flag
        if output_path.exists() and not args.regenerate:
            logger.error(f"Output file {output_path} already exists. Use --regenerate to overwrite.")
            return 1

        # Get specific args and global device arg
        threshold = getattr(args, 'threshold', 0.5)
        batch_size = getattr(args, 'batch_size', 8)
        device = getattr(args, 'device', None) # Pass device from global arg

        logger.info(f"Detecting shots in {video_path}...")
        logger.info(f"Threshold: {threshold}, Batch Size: {batch_size}, Device: {device or 'auto'}")

        # Run shot detection (assuming detect_shots uses the device arg)
        result = detect_shots(
            video_path=video_path,
            threshold=threshold,
            batch_size=batch_size,
            device=device # Pass the device
        )

        if result["success"]:
            # Write results to JSON file
            logger.info(f"Saving results to {output_path}...")
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info("Shot detection complete:")
            logger.info(f"- Found {len(result['shots'])} shots")
            logger.info(f"- Results saved to: {output_path}")
            return 0
        else:
            logger.error(f"Shot detection failed: {result.get('message', 'Unknown error')}")
            return 1

    except AttributeError as e:
        logger.error(f"Missing expected argument: {e}")
        return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if logger.level == logging.DEBUG:
            traceback.print_exc()
        return 1


def extract_frame_tags_main(args):
    """CLI entry point for extracting tags from frame images."""
    logger = setup_logger(args)

    if Interrogator is None:
        logger.error("WD14 Tagger components could not be imported. Cannot extract tags.")
        return 1

    try:
        frames_dir = Path(args.frames_dir)
        if not frames_dir.is_dir():
            logger.error(f"Frames directory not found: {frames_dir}")
            return 1

        # Handle optional output dir, defaulting to frames_dir
        output_dir = Path(args.output_dir) if hasattr(args, 'output_dir') and args.output_dir else frames_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory for tags: {output_dir}")

        model_name = getattr(args, 'model', 'wd14-convnextv2.v1') # Default from main.py
        threshold = getattr(args, 'threshold', 0.35) # Default from main.py
        device = getattr(args, 'device', None) # Global device arg
        regenerate = getattr(args, 'regenerate', False) # Global regenerate arg
        progress_bar = getattr(args, 'progress_bar', False) # Global progress bar arg

        logger.info(f"Using model: {model_name}, Threshold: {threshold}, Device: {device or 'auto'}")

        # Initialize the tagger
        logger.info("Initializing WD14 tagger...")
        try:
            if model_name in interrogators:
                # Pass the device argument to the tagger's initialization or interrogate method
                # This depends on how the wd14-tagger library is implemented.
                # Assuming the Interrogator class or interrogate method accepts a device param.
                # If not, this part needs adjustment based on the tagger's API.
                tagger = interrogators[model_name] # .setup(device=device)? Or pass device to interrogate?

                if tagger is None: # Check if interrogators dict might contain None
                     raise ValueError(f"Interrogator for {model_name} is None.")

                logger.debug(f"Tagger {model_name} initialized.")
            else:
                raise ValueError(f"Unknown model: {model_name}")

            # Initialize tag expander only if available
            expander = None
            if TagExpander:
                logger.info("Initializing tag expander...")
                # Pass args like cache_dir, credentials if needed and available globally
                # expander = TagExpander(log_level=logger.level) # Example
                expander = TagExpander() # Assuming default init is sufficient
                logger.debug("Tag expander initialized.")
            else:
                logger.warning("Tag expander not available, skipping tag expansion.")

        except Exception as e:
            logger.error(f"Error initializing tagger/expander: {e}")
            if logger.level == logging.DEBUG:
                traceback.print_exc()
            return 1

        # Find image files
        logger.info(f"Scanning for images in {frames_dir}...")
        image_suffixes = {'.jpg', '.jpeg', '.png', '.webp'}
        image_files = sorted([
            f for f in frames_dir.iterdir()
            if f.is_file() and f.suffix.lower() in image_suffixes
        ])

        if not image_files:
            logger.warning(f"No image files found in {frames_dir}")
            return 0
        logger.info(f"Found {len(image_files)} image files.")

        # Process images
        total_processed = 0
        total_skipped = 0
        files_iter = tqdm(image_files, desc="Processing frames", disable=not progress_bar)

        for img_file in files_iter:
            json_file = output_dir / f"{img_file.stem}.json"

            # Skip if exists and not regenerating
            if json_file.exists() and not regenerate:
                logger.debug(f"Skipping existing: {json_file}")
                total_skipped += 1
                continue

            try:
                logger.debug(f"Processing {img_file.name}...")
                img = Image.open(img_file)

                # Get predictions (pass device if available)
                # Note: Ensure the specific interrogator implementation supports the device argument
                if device:
                    ratings, raw_tags = tagger.interrogate(img, device=device)
                else:
                    ratings, raw_tags = tagger.interrogate(img)

                # Filter raw tags based on threshold AFTER getting them
                filtered_raw_tags = {tag: score for tag, score in raw_tags.items() if score >= threshold}

                expanded_tags_list = []
                tag_frequencies_dict = {}

                # Expand tags if expander is available and we have tags
                if expander and filtered_raw_tags:
                     logger.debug(f"Expanding {len(filtered_raw_tags)} tags for {img_file.name}...")
                     selected_tags = list(filtered_raw_tags.keys())
                     try:
                         expanded_tags_set, tag_frequencies = expander.expand_tags(selected_tags)
                         expanded_tags_list = sorted(list(expanded_tags_set))
                         tag_frequencies_dict = {tag: count for tag, count in tag_frequencies.items()}
                     except Exception as exp_e:
                         logger.warning(f"Failed to expand tags for {img_file.name}: {exp_e}")
                         # Fallback: use raw tags if expansion fails? Or leave empty?
                         expanded_tags_list = sorted(list(filtered_raw_tags.keys())) # Fallback to filtered raw tags

                elif filtered_raw_tags:
                    # No expander, just use the filtered raw tags
                    expanded_tags_list = sorted(list(filtered_raw_tags.keys()))
                    tag_frequencies_dict = {tag: 1 for tag in expanded_tags_list} # Basic frequency

                # Save results
                output_data = {
                    'image': str(img_file),
                    'model': model_name, # Record model used
                    'threshold': threshold,
                    'ratings': ratings,
                    'raw_tags': filtered_raw_tags, # Save filtered raw tags
                    'expanded_tags': expanded_tags_list,
                    'tag_frequencies': tag_frequencies_dict
                }
                with open(json_file, 'w') as f:
                    json.dump(output_data, f, indent=2)

                total_processed += 1

            except Exception as e:
                logger.error(f"Error processing {img_file.name}: {e}")
                if logger.level == logging.DEBUG:
                     traceback.print_exc()
                continue

        logger.info(f"Complete: {total_processed} images processed, {total_skipped} skipped. Results saved to {output_dir}")
        return 0

    except AttributeError as e:
        logger.error(f"Missing expected argument: {e}")
        return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if logger.level == logging.DEBUG:
            traceback.print_exc()
        return 1


def extract_shot_tags_main(args):
    """CLI entry point for aggregating frame tags into shot-level tags."""
    logger = setup_logger(args)

    try:
        shots_path = Path(args.shots_file) # Standardized name
        if not shots_path.is_file():
            logger.error(f"Shots file not found: {shots_path}")
            return 1

        tags_dir = Path(args.tags_dir) # Use new standardized name
        if not tags_dir.is_dir():
            logger.error(f"Frame tags directory not found: {tags_dir}")
            return 1

        # Use standardized output dir arg, handle default if not required in main.py
        if hasattr(args, 'output_dir') and args.output_dir:
             output_dir = Path(args.output_dir)
        else:
             output_dir = shots_path.parent / f"{shots_path.stem}_shot_tags"
             logger.info(f"Output directory not specified, defaulting to: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

        min_frames = getattr(args, 'min_frames', 1) # Default from main.py
        progress_bar = getattr(args, 'progress_bar', False) # Global progress bar arg

        logger.info(f"Aggregating tags from {tags_dir} based on {shots_path}...")
        logger.info(f"Output directory: {output_dir}, Min frames per tag: {min_frames}")

        # Load shots data
        try:
            with open(shots_path) as f:
                shots_data = json.load(f)
            if 'shots' not in shots_data or not isinstance(shots_data['shots'], list):
                logger.error(f"Invalid shots file format: Missing or invalid 'shots' list in {shots_path}")
                return 1
            shots = shots_data['shots']
        except json.JSONDecodeError as e:
            logger.error(f"Error reading shots JSON file {shots_path}: {e}")
            return 1
        except Exception as e:
            logger.error(f"Error loading shots data from {shots_path}: {e}")
            return 1

        # Process each shot
        shots_iter = tqdm(list(enumerate(shots)), desc="Aggregating shots", disable=not progress_bar)
        total_processed = 0
        total_skipped = 0
        total_warnings = 0

        for i, shot in shots_iter:
            # Validate shot structure minimally
            if not isinstance(shot, dict) or 'start_frame' not in shot or 'end_frame' not in shot:
                logger.warning(f"Skipping invalid shot data at index {i}: {shot}")
                total_warnings += 1
                continue

            shot_output_json = output_dir / f"shot_{i:04d}.json"

            if shot_output_json.exists() and not args.regenerate:
                logger.debug(f"Skipping existing: {shot_output_json}")
                total_skipped += 1
                continue

            logger.debug(f"Processing shot {i} (frames {shot['start_frame']}-{shot['end_frame']})")

            # Find all frame JSON files for this shot using the standard pattern
            # Assumes frame tag JSONs follow the same naming convention as frames
            frame_pattern = f"tc_*_shot{i:04d}.json"
            logger.debug(f"Searching for frame tag files in: {tags_dir} with pattern: {frame_pattern}")
            frame_files = sorted(tags_dir.glob(frame_pattern))
            logger.debug(f"Glob found {len(frame_files)} files matching pattern.")

            # Add fallback for legacy naming if needed (consider removing eventually)
            if not frame_files:
                legacy_pattern = f"frame*_shot{i:04d}.json"
                logger.debug(f"No files found with primary pattern, trying legacy: {legacy_pattern}")
                frame_files = sorted(tags_dir.glob(legacy_pattern))
                if frame_files:
                    logger.info(f"Found {len(frame_files)} files using legacy pattern {legacy_pattern} for shot {i}")
                else:
                    logger.warning(f"No frame tag files found for shot {i} using patterns '{frame_pattern}' or '{legacy_pattern}' in {tags_dir}")
                    total_warnings += 1
                    continue # Skip shot if no frame tags found


            # Aggregate tags from found frame files
            tag_counts: dict[str, int] = {}
            processed_frame_count = 0

            for frame_json_path in frame_files:
                try:
                    with open(frame_json_path) as f:
                        frame_data = json.load(f)

                    # Aggregate from 'expanded_tags' (or 'raw_tags' as fallback?)
                    tags_to_aggregate = frame_data.get('expanded_tags')
                    if tags_to_aggregate is None:
                        # Fallback or warning?
                        tags_to_aggregate = list(frame_data.get('raw_tags', {}).keys())
                        if tags_to_aggregate:
                             logger.debug(f"Using raw_tags for {frame_json_path.name} as expanded_tags not found.")

                    if isinstance(tags_to_aggregate, list):
                        for tag in tags_to_aggregate:
                            if isinstance(tag, str): # Basic validation
                                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                            else:
                                logger.warning(f"Non-string tag found in {frame_json_path.name}: {tag}")
                    else:
                         logger.warning(f"Expected a list for 'expanded_tags' in {frame_json_path.name}, found {type(tags_to_aggregate)}. Skipping tags for this frame.")

                    processed_frame_count += 1

                except json.JSONDecodeError as e:
                    logger.error(f"Error reading JSON from {frame_json_path}: {e}")
                    total_warnings += 1
                    continue # Skip corrupted file
                except Exception as e:
                    logger.error(f"Unexpected error processing {frame_json_path}: {e}")
                    if logger.level == logging.DEBUG:
                         traceback.print_exc()
                    total_warnings += 1
                    continue # Skip file on unexpected error

            if processed_frame_count == 0:
                logger.warning(f"No valid frame tag files processed for shot {i}")
                total_warnings += 1
                continue # Skip shot if no frames were processed

            # Filter tags by minimum frame threshold
            final_shot_tags = {
                tag: count
                for tag, count in tag_counts.items()
                if count >= min_frames
            }

            # Save shot tags
            shot_output_data = {
                'shot_index': i,
                'start_frame': shot['start_frame'],
                'end_frame': shot['end_frame'],
                'processed_frame_count': processed_frame_count,
                'tags': final_shot_tags,
                'tags_threshold': min_frames,
            }
            logger.debug(f"Saving aggregated data for shot {i} to {shot_output_json}")
            with open(shot_output_json, 'w') as f:
                json.dump(shot_output_data, f, indent=2)

            total_processed += 1

        logger.info(f"Aggregation complete: {total_processed} shots processed, {total_skipped} skipped, {total_warnings} warnings. Results saved to {output_dir}")
        return 0 # Success even with warnings

    except AttributeError as e:
        logger.error(f"Missing expected argument: {e}")
        return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if logger.level == logging.DEBUG:
            traceback.print_exc()
        return 1


# Remove the direct script execution block (__name__ == "__main__")
# All commands should be run via the main avtools entry point now.
