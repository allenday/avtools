"""
Video FCPXML generation module for shot detection data.
"""

import json
import xml.etree.ElementTree as ET
from decimal import Decimal, getcontext
from pathlib import Path

# Import common utilities
from avtools.common.fcpxml_utils import (
    DEFAULT_FRAME_RATE,
    create_base_fcpxml,
    prettify_xml,
    seconds_to_asset_duration,
    seconds_to_timeline_time,
    snap_to_frame_grid,
)
from avtools.common.ffmpeg_utils import get_video_info

# Configure decimal precision
getcontext().prec = 20


def json_to_fcpxml(input_json_path, output_fcpxml_path=None, video_path=None, frame_rate=None):
    """
    Convert video shot detection JSON to FCPXML with frame-aligned markers.

    Parameters:
    - input_json_path: Path to input JSON file with shot data
    - output_fcpxml_path: Path to output FCPXML file (default: input path with .fcpxml extension)
    - video_path: Path to source video file (optional)
    - frame_rate: Frame rate to use (default: auto-detect from video or 50 fps)

    Returns:
    - True on success, False on failure
    """
    input_json_path_obj = Path(input_json_path)
    if not input_json_path_obj.is_file():
        print(f"Error: Input JSON file not found: {input_json_path_obj}")
        return False

    # Set output path if not provided
    if output_fcpxml_path is None:
        output_fcpxml_path = input_json_path_obj.with_suffix('.fcpxml')
    else:
        output_fcpxml_path = Path(output_fcpxml_path)

    # Load JSON data
    try:
        with open(input_json_path_obj, encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False

    # Get video info
    video_info = None
    try:
        # First check if path exists in the JSON data - try both 'path' and 'video_path' keys
        video_path_str = data.get('path')
        if not video_path_str:
            video_path_str = data.get('video_path')  # Also check for video_path key

        if video_path_str and Path(video_path_str).exists():
            print(f"Using path from JSON data: {video_path_str}")
        # If not in JSON, use provided path
        elif video_path:
            video_path_str = str(video_path)
            print(f"Using provided video path: {video_path_str}")
        # Otherwise try to derive from JSON file name
        else:
            video_filename = input_json_path_obj.stem
            video_path_guess = input_json_path_obj.parent / f"{video_filename}.mp4"  # Assume MP4 extension
            if video_path_guess.exists():
                video_path_str = str(video_path_guess)
                print(f"Using derived video path: {video_path_str}")
            else:
                video_path_str = None

        if video_path_str and Path(video_path_str).exists():
            video_info = get_video_info(video_path_str)
        else:
            # Create minimal video info with default values
            print("Warning: No video file specified or found. Using default video parameters.")

            # Get maximum shot time from data for default duration
            max_time = 0
            for shot in data.get('shots', []):
                shot_end = float(shot['time_offset']) + float(shot['time_duration'])
                max_time = max(max_time, shot_end)

            video_info = {
                'duration': str(max_time + 1),
                'fps': str(DEFAULT_FRAME_RATE if frame_rate is None else frame_rate),
                'width': '1920',
                'height': '1080'
            }
    except Exception as e:
        print(f"Error determining video info: {e}")
        # Create minimal video info with default values
        video_info = {
            'duration': '60',  # Default 60 second duration
            'fps': str(DEFAULT_FRAME_RATE if frame_rate is None else frame_rate),
            'width': '1920',
            'height': '1080'
        }

    # Create FCPXML
    return create_fcpxml_from_data(data, video_info, output_fcpxml_path, input_json_path_obj, frame_rate, video_path_str)


def create_fcpxml_from_data(json_data, video_info, output_fcpxml_path, input_json_path_obj, frame_rate=None, video_path_str=None):
    """Creates FCPXML v1.13 with frame-aligned markers and video shots."""
    if video_info is None:
        print("Error: Cannot proceed without video information.")
        return False

    # Use provided frame rate or detected frame rate from video
    if frame_rate is None:
        try:
            frame_rate = float(video_info['fps'])
            print(f"Using detected frame rate from video: {frame_rate}")
        except (KeyError, ValueError):
            frame_rate = DEFAULT_FRAME_RATE
            print(f"Could not determine frame rate from video, using default: {frame_rate}")

    # Ensure frame rate is an integer or simple fraction for exact frame boundaries
    if frame_rate == int(frame_rate):
        frame_rate = int(frame_rate)

    # Get video dimensions
    try:
        width = int(video_info['width'])
        height = int(video_info['height'])
    except (KeyError, ValueError):
        width = 1920
        height = 1080
        print(f"Could not determine dimensions from video, using default: {width}x{height}")

    # Calculate integer timebase from frame rate to ensure exact frame boundaries
    if frame_rate == int(frame_rate):
        # For integer frame rates, use a simple timebase that guarantees exact frame boundaries
        timebase = str(frame_rate * 100)  # Use 100 × frame rate for simpler calculations
        frame_duration = f"100/{timebase}s"
    else:
        # For non-integer frame rates, find a suitable timebase
        # Common non-integer rates like 29.97 or 23.976 need special handling
        if abs(frame_rate - 29.97) < 0.01:  # NTSC 29.97 fps
            timebase = "30000"
            frame_duration = "1001/30000s"
            frame_rate = Decimal('30000') / Decimal('1001')  # Set exact frame rate
        elif abs(frame_rate - 23.976) < 0.01:  # Film 23.976 fps
            timebase = "24000"
            frame_duration = "1001/24000s"
            frame_rate = Decimal('24000') / Decimal('1001')  # Set exact frame rate
        else:
            # For other non-integer rates, use a large timebase for higher precision
            timebase = str(int(frame_rate * 10000))
            frame_duration = f"{10000}/{timebase}s"

    # Fixed size for markers (1 frame duration)
    marker_frame_duration = f"1/{timebase}s"

    # Get video filename from path
    if video_path_str:
        video_filename = Path(video_path_str).name
    else:
        video_filename = input_json_path_obj.stem + ".mp4"  # Default name based on JSON

    # Create URI for FCPXML (using absolute path)
    video_uri = str(Path(video_path_str).absolute().as_uri()) if video_path_str else ""
    if video_uri:
        print(f"--- Asset URI: {video_uri} ---")
    else:
        print("--- No video URI available ---")

    # Get shots from the JSON data
    shots = json_data.get('shots', [])
    if not shots:
        print("Error: No shots found in the JSON data.")
        return False

    # Extract asset info
    asset_native_duration_sec = Decimal(str(video_info['duration']))
    asset_native_fps = Decimal(str(video_info['fps']))
    asset_duration_fcpxml = seconds_to_asset_duration(asset_native_duration_sec, asset_native_fps)

    # First process all shots to establish frame-aligned boundaries
    processed_shots = []
    for i, shot in enumerate(shots):
        shot_start_sec = Decimal(str(shot['time_offset']))
        shot_duration_sec = Decimal(str(shot['time_duration']))
        shot_prob = shot.get('probability', 0)

        # Snap times to frame grid
        snapped_start_sec = snap_to_frame_grid(shot_start_sec, frame_rate)
        snapped_end_sec = snap_to_frame_grid(shot_start_sec + shot_duration_sec, frame_rate)

        processed_shots.append({
            'index': i,
            'start_sec': snapped_start_sec,
            'end_sec': snapped_end_sec,
            'prob': shot_prob
        })

    # Sort shots by start time to ensure proper sequencing
    processed_shots.sort(key=lambda x: x['start_sec'])

    # Calculate max event time
    if processed_shots:
        max_event_time_sec = max([shot['end_sec'] for shot in processed_shots])
    else:
        max_event_time_sec = Decimal('0.0')

    # Calculate total timeline duration
    timeline_duration_sec = max(asset_native_duration_sec, max_event_time_sec)
    timeline_duration_sec = snap_to_frame_grid(timeline_duration_sec, frame_rate)
    total_timeline_duration_fcpxml = seconds_to_timeline_time(timeline_duration_sec, timebase, frame_rate, round_up=True)
    print(f"Timeline Duration: {timeline_duration_sec}s -> {total_timeline_duration_fcpxml}")

    # Build FCPXML structure
    format_id_video = "r1"
    format_name = f"FFVideoFormat{height}p{int(frame_rate) if frame_rate == int(frame_rate) else frame_rate}"
    event_name = f"{video_filename}_Shots"
    project_name = f"{video_filename}_Shots"

    # Create base FCPXML structure
    fcpxml, resources, spine, gap, effect_id_placeholder = create_base_fcpxml(
        format_id=format_id_video,
        format_name=format_name,
        frame_duration=frame_duration,
        width=str(width),
        height=str(height),
        timebase=timebase,
        event_name=event_name,
        project_name=project_name,
        total_timeline_duration=total_timeline_duration_fcpxml
    )

    # Define video asset
    asset_id_video = "r2"
    asset = ET.SubElement(resources, 'asset', id=asset_id_video, name=video_filename,
                        start="0s", duration=asset_duration_fcpxml,
                        hasVideo="1", hasAudio="1", audioSources="1", audioChannels="2",
                        format=format_id_video)
    if video_uri:
        ET.SubElement(asset, 'media-rep', kind='original-media', src=video_uri)
    else:
        # Always add a media-rep element to satisfy DTD requirements
        # Use file:// protocol with a placeholder path that won't be used
        placeholder_uri = "file:///placeholder_video_path.mp4"
        ET.SubElement(asset, 'media-rep', kind='original-media', src=placeholder_uri)
        print(f"Warning: No video path available. Using placeholder media-rep with src={placeholder_uri}")

    # Add the main video asset to lane 2
    asset_clip_video = ET.SubElement(gap, 'asset-clip', name=video_filename,
                                   ref=asset_id_video, lane="2", offset="0s",
                                   duration=total_timeline_duration_fcpxml)

    # Now create markers and clips with adjusted durations to ensure no gaps
    for i, shot_info in enumerate(processed_shots):
        shot_start_sec = shot_info['start_sec']
        shot_prob = shot_info['prob']
        original_end_sec = shot_info['end_sec']

        # For all but the last shot, extend end time to the start of the next shot
        if i < len(processed_shots) - 1:
            next_start_sec = processed_shots[i + 1]['start_sec']
            shot_end_sec = next_start_sec
        else:
            # For the last shot, use the original end time
            shot_end_sec = original_end_sec

        # Calculate actual duration
        shot_duration_sec = shot_end_sec - shot_start_sec

        start_fcpxml = seconds_to_timeline_time(shot_start_sec, timebase, frame_rate, round_up=False)
        marker_name = f"Shot {shot_info['index'] + 1}"
        marker_note = f"Start: {shot_start_sec}s, Duration: {shot_duration_sec}s, Prob: {shot_prob:.2f}"

        ET.SubElement(asset_clip_video, 'marker', start=start_fcpxml,
                    duration=marker_frame_duration, value=marker_name, note=marker_note)

        # Calculate shot offset and duration
        placeholder_offset_fcpxml = seconds_to_timeline_time(shot_start_sec, timebase, frame_rate, round_up=False)
        placeholder_duration_fcpxml = seconds_to_timeline_time(shot_duration_sec, timebase, frame_rate, round_up=True)

        print(f"Shot {shot_info['index'] + 1}: Offset={placeholder_offset_fcpxml}, Duration={placeholder_duration_fcpxml}, Prob={shot_prob:.2f}")

        # Create actual video segment for the shot (in lane 3)
        # This creates a clip that references the original video asset but shows just the shot segment
        shot_start_in_source_fcpxml = seconds_to_timeline_time(shot_start_sec, timebase, frame_rate, round_up=False)

        shot_clip = ET.SubElement(gap, 'asset-clip',
                                name=f"Shot {shot_info['index'] + 1}",
                                ref=asset_id_video,
                                lane="3",
                                offset=placeholder_offset_fcpxml,
                                duration=placeholder_duration_fcpxml,
                                start=shot_start_in_source_fcpxml)

        # Add a marker at the start of the actual video clip
        ET.SubElement(shot_clip, 'marker',
                    start="0s",
                    duration=marker_frame_duration,
                    value=f"Shot {shot_info['index'] + 1}",
                    note="Extracted segment")

    # Write FCPXML file
    xml_string = prettify_xml(fcpxml)
    try:
        with open(output_fcpxml_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        print(f"Successfully created FCPXML v1.13 with {frame_rate}fps-aligned markers: {output_fcpxml_path}")
        return True
    except OSError as e:
        print(f"Error writing FCPXML: {e}")
        return False
