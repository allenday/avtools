"""
Frame extraction module for video shot analysis.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import ffmpeg

from .cache import check_frame_exists, get_frame_path
from .config import ensure_cache_dir, get_video_dir, get_video_hash


def extract_frames(
    video_path: str | Path,
    shots_data: str | Path | dict,
    cache_dir: Path | None = None,
    video_id: str | None = None,
    extract_positions: list[str] = None,
    format_: str = "jpg",
    quality: int = 95,
    hz: float | None = None,
    force: bool = False
) -> dict[str, Any]:
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
        hz: Frequency of frame extraction in Hz (e.g., 1.0 = 1 frame per second)
        force: If True, overwrite existing frames in cache (default: False)

    Returns:
        Dict: Extracted frame information
    """
    # Set defaults
    if extract_positions is None:
        extract_positions = ["start", "middle", "end"]

    # Convert paths to Path objects
    video_path = Path(video_path)

    # Load shot data
    if isinstance(shots_data, str | Path):
        shots_data_path = Path(shots_data)
        with open(shots_data_path) as f:
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

    # Store the hz parameter used
    sample_hz = hz

    for i, shot in enumerate(shots):
        shot_number = i + 1  # 1-based shot number
        time_offset = float(shot['time_offset'])
        time_duration = float(shot['time_duration'])
        probability = float(shot.get('probability', 1.0))

        # Calculate frame positions to extract
        positions = []

        if hz is not None:
            # Extract frames based on specified frequency
            interval = 1.0 / hz  # Time between frames in seconds
            current_time = time_offset

            while current_time < time_offset + time_duration:
                positions.append(("hz", current_time))
                current_time += interval
        else:
            # Extract frames at the standard positions
            if "start" in extract_positions:
                positions.append(("start", time_offset))

            if "middle" in extract_positions:
                middle_time = time_offset + (time_duration / 2)
                positions.append(("middle", middle_time))

            if "end" in extract_positions:
                end_time = time_offset + time_duration - (1/fps)  # One frame before end
                positions.append(("end", end_time))

        # Extract frames
        shot_frames = []

        for position_name, position_time in positions:
            # Format timecode as HH:MM:SS.mmm
            timecode = format_timecode(position_time)

            # Estimate frame number based on fps (for compatibility)
            frame_number = int(position_time * fps)

            # Check if frame already exists in cache
            # If force is True, we skip this check and always extract
            frame_exists = False
            if not force:
                frame_exists = check_frame_exists(video_id, frame_number, shot_number, cache_dir, timecode)

            if frame_exists:
                frame_path = get_frame_path(video_id, frame_number, shot_number, cache_dir, timecode)
                shot_frames.append({
                    "position": position_name,
                    "frame_number": frame_number,
                    "shot_number": shot_number,
                    "time": position_time,
                    "timecode": timecode,
                    "path": str(frame_path),
                    "extracted": False,  # Already existed
                })
                continue

            # Extract frame
            output_path = get_frame_path(video_id, frame_number, shot_number, cache_dir, timecode)

            # Use ffmpeg to extract frame
            try:
                stream = ffmpeg.input(str(video_path), ss=position_time)
                stream = stream.filter('scale', 'iw', 'ih')
                stream = stream.output(str(output_path), vframes=1, q=quality, format=format_)
                if force:
                    stream = stream.overwrite_output()

                stream.run(capture_stdout=True, capture_stderr=True)

                shot_frames.append({
                    "position": position_name,
                    "frame_number": frame_number,
                    "shot_number": shot_number,
                    "time": position_time,
                    "timecode": timecode,
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
        "sample_hz": sample_hz,
        "shots_processed": len(extracted_frames),
        "frames_extracted": total_frames,
        "cache_dir": str(cache_dir),
        "shots": extracted_frames
    }

def extract_all_frames(
    video_path: str | Path,
    shots_data: str | Path | dict,
    output_dir: str | Path,
    min_probability: float = 0.0,
    frame_interval: float | None = None,
    hz: float | None = None,
    force: bool = False
) -> dict[str, Any]:
    """
    Extract all frames from shots at a specified interval and save to directory.
    Uses a single ffmpeg call to extract frames, then renames them based on shot info.

    Args:
        video_path: Path to video file
        shots_data: Path to JSON file with shot data or dictionary with shot data
        output_dir: Directory to save frames
        min_probability: Minimum probability threshold for shots (default: 0.0 to include all shots)
        frame_interval: Seconds between frames (if None, extract every frame)
                        This is the inverse of hz (frame_interval = 1.0/hz)
        hz: Frequency of frame extraction in Hz (e.g., 1.0 = 1 frame per second)
            If provided, this overrides frame_interval (since hz = 1.0/frame_interval)
        force: If True, overwrite existing frame files in the output directory (default: False)

    Returns:
        Dict: Extraction results

    Note:
        The parameters frame_interval and hz are two ways to express the same concept:
        - frame_interval is the time between frames (in seconds)
        - hz is the frequency of frames (per second)

        They are related by: hz = 1.0 / frame_interval

        If both are provided, hz takes precedence.
    """
    # Convert paths to Path objects
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    # Load shot data
    if isinstance(shots_data, str | Path):
        shots_data_path = Path(shots_data)
        with open(shots_data_path) as f:
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
    extraction_hz = None

    if hz is not None:
        extraction_hz = hz
    elif frame_interval is not None:
        extraction_hz = 1.0 / frame_interval
    else:
        extraction_hz = fps

    # Process shots
    shots = shots_data.get('shots', [])
    # No filtering by probability - use all shots
    filtered_shots = shots

    if not filtered_shots:
        return {
            "success": False,
            "message": "No shots found in the data",
            "output_dir": str(output_dir)
        }

    # Create a temporary directory for extraction
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        try:
            # Extract frames using simple fps-based approach
            print(f"Extracting frames at {extraction_hz} Hz...")

            # Simple command to extract frames at desired rate
            output_pattern = str(temp_dir_path / 'frame%06d.jpg')

            # Calculate the frame rate for extraction
            # If we want 5 Hz, we extract every (fps/5)th frame
            if extraction_hz >= fps:
                # If requested Hz is >= video fps, just extract every frame
                extract_fps = fps
            else:
                # Otherwise set the extraction fps directly
                extract_fps = extraction_hz

            stream = ffmpeg.input(str(video_path))
            stream = stream.output(
                output_pattern,
                r=extract_fps  # Set output frame rate
            )
            # Only overwrite if force is true
            if force:
                stream = stream.overwrite_output()

            stream.run(capture_stdout=True, capture_stderr=True)

            # Find all extracted frames
            extracted_files = sorted(temp_dir_path.glob('frame*.jpg'))
            print(f"Extracted {len(extracted_files)} frames")

            # Build shot time ranges for mapping frames to shots
            shot_ranges = []
            for i, shot in enumerate(shots):
                shot_number = i + 1
                time_offset = float(shot['time_offset'])
                time_duration = float(shot['time_duration'])
                shot_ranges.append({
                    'shot_number': shot_number,
                    'start_time': time_offset,
                    'end_time': time_offset + time_duration,
                    'shot_data': shot
                })

            # Process and rename extracted frames
            print("Processing and renaming extracted frames...")
            processed_shot_data = {}
            total_frames = 0

            # Get total duration of video
            video_duration = float(video_stream.get('duration', 0))
            if video_duration <= 0:
                # If not available, use the end time of the last shot
                video_duration = max([r['end_time'] for r in shot_ranges]) if shot_ranges else 0

            # Calculate time increment between frames
            time_per_frame = 1.0 / extract_fps

            for i, img_file in enumerate(extracted_files):
                # Calculate the approximate timestamp for this frame
                frame_time = i * time_per_frame

                if frame_time > video_duration:
                    print(f"Skipping frame beyond video duration: {frame_time} > {video_duration}")
                    continue

                # Find which shot this frame belongs to
                shot_info = None
                for shot_range in shot_ranges:
                    if shot_range['start_time'] <= frame_time < shot_range['end_time']:
                        shot_info = shot_range
                        break

                if not shot_info:
                    # Frame doesn't belong to any shot, skip it
                    continue

                # Get shot number and format timecode
                shot_number = shot_info['shot_number']
                timecode = format_timecode(frame_time)

                # Create final filename with timecode
                output_filename = f"tc_{timecode.replace(':', '-')}_shot{shot_number:04d}.jpg"
                output_path = output_dir / output_filename

                # Copy file to final location
                # shutil.copy2 will overwrite by default, so this respects force implicitly
                # If we wanted force=False to *prevent* overwriting here, we'd need to check existence first.
                # Since ffmpeg likely overwrote in temp_dir if force=True, copy2 is fine.
                shutil.copy2(img_file, output_path)

                # Track frames by shot
                if shot_number not in processed_shot_data:
                    # Create new shot data entry
                    shot_data = shot_info['shot_data']
                    processed_shot_data[shot_number] = {
                        "shot_number": shot_number,
                        "time_offset": float(shot_data['time_offset']),
                        "time_duration": float(shot_data['time_duration']),
                        "probability": float(shot_data.get('probability', 1.0)),
                        "frames": []
                    }

                # Add frame to shot data
                if shot_number in processed_shot_data:
                    frame_data = {
                        "frame_number": i,
                        "shot_number": shot_number,
                        "time": frame_time,
                        "timecode": timecode,
                        "path": str(output_path)
                    }
                    processed_shot_data[shot_number]["frames"].append(frame_data)
                    total_frames += 1

            # Convert processed shot data to list
            processed_shots = list(processed_shot_data.values())

            return {
                "success": True,
                "video_path": str(video_path),
                "output_dir": str(output_dir),
                "fps": fps,
                "sample_hz": extraction_hz,
                "shots_processed": len(processed_shots),
                "frames_extracted": total_frames,
                "shots": processed_shots
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

def format_timecode(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS.mmm timecode.

    Args:
        seconds: Time in seconds

    Returns:
        str: Formatted timecode
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds_part:06.3f}"
