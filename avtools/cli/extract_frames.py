"""
CLI command for extracting frames from video shots.
"""

import json
import logging
import traceback  # For debug logging
from pathlib import Path

from ..video.cache import clear_cache, get_cache_info

# Import library functions
from ..video.frames import extract_all_frames, extract_frames

# Import shared logger setup
from .video_commands import setup_logger

# Module-level logger (configured by setup_logger)
logger = logging.getLogger('avtools.cli')


def check_path(path_obj: Path, is_dir: bool = False, check_exists: bool = True, logger_instance: logging.Logger = logger) -> bool:
    """Checks if a path exists and is the correct type (file/dir). Logs error and returns False on failure."""
    if check_exists:
        if not path_obj.exists():
            logger_instance.error(f"{( 'Directory' if is_dir else 'File')} not found: {path_obj}")
            return False
        if is_dir and not path_obj.is_dir():
            logger_instance.error(f"Expected a directory but found a file: {path_obj}")
            return False
        if not is_dir and not path_obj.is_file():
             logger_instance.error(f"Expected a file but found a directory: {path_obj}")
             return False
    # Optional: Add checks for read/write permissions if needed
    return True


def main(args):
    """Main entry point for frame caching (was extract-frames).
    Relies on args parsed by main.py.

    Args:
        args: Parsed argument namespace from main.py

    Returns:
        int: 0 on success, 1 on failure
    """
    logger = setup_logger(args)

    try:
        # Use standardized argument names from args
        video_path = Path(args.video_file)
        shots_data_path = Path(args.shots_file)

        # Use helper for validation
        if not check_path(video_path, logger_instance=logger):
            return 1
        if not check_path(shots_data_path, logger_instance=logger):
            return 1

        # Access optional args safely using getattr with defaults
        cache_dir = Path(args.cache_dir) if getattr(args, 'cache_dir', None) else None
        video_id = getattr(args, 'video_id', None)
        positions_str = getattr(args, 'positions', "start,middle,end")
        extract_positions = [pos.strip() for pos in positions_str.split(",")]
        format_ = getattr(args, 'format', "jpg")
        quality = getattr(args, 'quality', 95)
        hz = getattr(args, 'hz', None)
        json_output = getattr(args, 'json_output', False)
        # Global args
        regenerate = getattr(args, 'regenerate', False)

        logger.info(f"Caching frames for {video_path} based on {shots_data_path}...")
        logger.info(f"Positions: {extract_positions}, Format: {format_}, Quality: {quality}")
        if hz:
             logger.info(f"Frequency (Hz): {hz} (overrides positions if specified)")
        logger.info(f"Cache directory: {cache_dir or 'Default'}")
        if regenerate:
            logger.warning("Regenerate flag is set. Existing cache entries for these frames will be overwritten.")

        # Run extraction (caching logic)
        # Pass regenerate if the underlying function supports it
        result = extract_frames(
            video_path=video_path,
            shots_data=shots_data_path,
            cache_dir=cache_dir,
            video_id=video_id,
            extract_positions=extract_positions,
            format_=format_,
            quality=quality,
            hz=hz,
            regenerate=regenerate # Pass regenerate flag
        )

        # Output results
        if json_output:
            # Ensure result is serializable (convert Path objects if any)
            serializable_result = {
                k: str(v) if isinstance(v, Path) else v
                for k, v in result.items()
            }
            print(json.dumps(serializable_result, indent=2))
        else:
            if result.get("success", False):
                logger.info(f"Successfully processed {result.get('shots_processed', 'N/A')} shots")
                logger.info(f"Extracted {result.get('frames_extracted', 'N/A')} frames")
                logger.info(f"Video ID: {result.get('video_id', 'N/A')}")
                if 'sample_hz' in result and result['sample_hz']:
                    logger.info(f"Sampling frequency: {result['sample_hz']} Hz")
                cache_loc = result.get('cache_dir', 'N/A')
                logger.info(f"Frames saved to cache: {cache_loc}")
            else:
                logger.error(f"Frame caching failed: {result.get('message', 'Unknown error')}")

        return 0 if result.get("success", False) else 1

    except AttributeError as e:
        logger.error(f"Missing expected argument: {e}")
        return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred during frame caching: {e}")
        if logger.level == logging.DEBUG:
            traceback.print_exc()
        return 1


def extract_all_frames_main(args):
    """CLI entry point for extracting all frames to a directory.
    Relies on args parsed by main.py.

    Args:
        args: Parsed argument namespace from main.py

    Returns:
        int: 0 on success, 1 on failure
    """
    logger = setup_logger(args)

    try:
        # Use standardized argument names from args
        video_path = Path(args.video_file)
        shots_data_path = Path(args.shots_file)
        output_dir = Path(args.output_dir) # Required by parser

        # Use helper for validation
        if not check_path(video_path, logger_instance=logger):
            return 1
        if not check_path(shots_data_path, logger_instance=logger):
            return 1
        # Check output dir existence *before* mkdir - check_path(..., check_exists=False)? No, just mkdir.
        output_dir.mkdir(parents=True, exist_ok=True)

        # Access optional/specific args safely
        min_probability = getattr(args, 'min_probability', 0.0)
        frame_interval = getattr(args, 'frame_interval', None)
        hz = getattr(args, 'hz', None)
        json_output = getattr(args, 'json_output', False)
        # Global args
        regenerate = getattr(args, 'regenerate', False)

        logger.info(f"Extracting frames for {video_path} based on {shots_data_path}...")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Minimum shot probability: {min_probability}")
        if hz:
            logger.info(f"Using frequency: {hz} Hz")
        elif frame_interval:
            logger.info(f"Using interval: {frame_interval} seconds")
        else:
             logger.info("Extracting every frame within shots.")
        if regenerate:
            logger.warning("Regenerate flag is set. Existing frames in output directory may be overwritten (or dir cleared).")

        # Run extraction for all frames
        # Pass regenerate if the underlying function supports it
        result = extract_all_frames(
            video_path=video_path,
            shots_data=shots_data_path,
            output_dir=output_dir,
            min_probability=min_probability,
            frame_interval=frame_interval,
            hz=hz,
            regenerate=regenerate # Pass regenerate flag
        )

        # Output results
        if json_output:
             # Ensure result is serializable
            serializable_result = {
                k: str(v) if isinstance(v, Path) else v
                for k, v in result.items()
            }
            print(json.dumps(serializable_result, indent=2))
        else:
            if result.get("success", False):
                logger.info(f"Successfully processed {result.get('shots_processed', 'N/A')} shots")
                logger.info(f"Extracted {result.get('frames_extracted', 'N/A')} frames")
                logger.info(f"Video ID used (if cached): {result.get('video_id', 'N/A')}")
                if 'sample_hz' in result and result['sample_hz']:
                     logger.info(f"Sampling frequency: {result['sample_hz']} Hz")
                out_loc = result.get('output_dir', 'N/A')
                logger.info(f"Frames saved to: {out_loc}")
            else:
                logger.error(f"Frame extraction failed: {result.get('message', 'Unknown error')}")

        return 0 if result.get("success", False) else 1

    except AttributeError as e:
        logger.error(f"Missing expected argument: {e}")
        return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred during frame extraction: {e}")
        if logger.level == logging.DEBUG:
            traceback.print_exc()
        return 1


def cache_list_main(args):
    """CLI entry point for listing cached frames.
    Relies on args parsed by main.py.

    Args:
        args: Parsed argument namespace from main.py

    Returns:
        int: 0 on success, 1 on failure
    """
    logger = setup_logger(args)

    try:
        cache_dir = Path(args.cache_dir) if getattr(args, 'cache_dir', None) else None
        json_output = getattr(args, 'json_output', False)

        logger.info(f"Listing cache contents for directory: {cache_dir or 'Default'}")

        # Use check_path to see if dir exists before calling get_cache_info if it errors on non-existent dirs
        # Assuming get_cache_info handles non-existence gracefully based on previous code.
        cache_info = get_cache_info(cache_dir)

        if json_output:
             # Ensure result is serializable (Path objects to strings)
            serializable_info = {
                'cache_directory': str(cache_info.get('cache_directory')),
                'total_size_bytes': cache_info.get('total_size_bytes'),
                'total_size_readable': cache_info.get('total_size_readable'),
                'video_count': cache_info.get('video_count'),
                'videos': [
                    {
                        'video_id': vid_id,
                        'frame_count': info.get('frame_count'),
                        'size_bytes': info.get('size_bytes'),
                        'size_readable': info.get('size_readable'),
                        'first_frame_time': info.get('first_frame_time').isoformat() if info.get('first_frame_time') else None,
                        'last_frame_time': info.get('last_frame_time').isoformat() if info.get('last_frame_time') else None,
                    }
                    for vid_id, info in cache_info.get('videos', {}).items()
                ]
            }
            print(json.dumps(serializable_info, indent=2))
        else:
            logger.info(f"Cache Directory: {cache_info.get('cache_directory')}")
            logger.info(f"Total Size: {cache_info.get('total_size_readable')} ({cache_info.get('total_size_bytes')} bytes)")
            logger.info(f"Video Count: {cache_info.get('video_count')}")
            if cache_info.get('videos'):
                logger.info("Cached Videos:")
                for vid_id, info in cache_info.get('videos', {}).items():
                    logger.info(f"  - ID: {vid_id}")
                    logger.info(f"    Frames: {info.get('frame_count')}")
                    logger.info(f"    Size: {info.get('size_readable')}")
                    first_time = info.get('first_frame_time')
                    last_time = info.get('last_frame_time')
                    logger.info(f"    Cached Between: {first_time.strftime('%Y-%m-%d %H:%M') if first_time else 'N/A'} and {last_time.strftime('%Y-%m-%d %H:%M') if last_time else 'N/A'}")
            else:
                logger.info("No videos found in cache.")

        return 0

    except FileNotFoundError:
        # Handled by check_path if we used it, or get_cache_info might raise it.
        logger.error(f"Cache directory not found: {cache_dir or 'Default location'}")
        return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing cache: {e}")
        if logger.level == logging.DEBUG:
            traceback.print_exc()
        return 1


def cache_clear_main(args):
    """CLI entry point for clearing cache.
    Relies on args parsed by main.py.

    Args:
        args: Parsed argument namespace from main.py

    Returns:
        int: 0 on success, 1 on failure
    """
    logger = setup_logger(args)

    try:
        cache_dir = Path(args.cache_dir) if getattr(args, 'cache_dir', None) else None
        older_than_days = getattr(args, 'older_than', None)
        json_output = getattr(args, 'json_output', False)
        # regenerate = getattr(args, 'regenerate', False) # Does clear_cache need a regenerate flag?

        logger.info(f"Clearing cache contents for directory: {cache_dir or 'Default'}")
        if older_than_days is not None:
            logger.info(f"Only clearing items older than {older_than_days} days.")

        # Perform cache clearing
        # Pass regenerate? clear_cache(..., regenerate=regenerate)
        clear_result = clear_cache(cache_dir, older_than_days)

        if json_output:
            print(json.dumps(clear_result, indent=2))
        else:
            logger.info(f"Items Removed: {clear_result.get('items_removed', 0)}")
            logger.info(f"Bytes Freed: {clear_result.get('bytes_freed', 0)} ({clear_result.get('size_readable', '0 B')})")
            if clear_result.get('errors'):
                logger.warning(f"Encountered {len(clear_result['errors'])} errors during clearing:")
                for err in clear_result['errors']:
                    logger.warning(f"  - {err}")

        return 0 # Return success even if there were non-fatal errors during deletion

    except FileNotFoundError:
        # If the goal is to clear, a non-existent directory isn't really an error
        logger.warning(f"Cache directory not found: {cache_dir or 'Default location'}. Nothing to clear.")
        if json_output:
            print(json.dumps({'items_removed': 0, 'bytes_freed': 0, 'size_readable': '0 B', 'errors': []}))
        return 0
    except Exception as e:
        logger.error(f"An unexpected error occurred while clearing cache: {e}")
        if logger.level == logging.DEBUG:
            traceback.print_exc()
        return 1
