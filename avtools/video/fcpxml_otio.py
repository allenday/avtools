"""
Video FCPXML generation module using otio-fcpx-xml-lite-adapter.
"""

import json
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

import opentimelineio as otio

from avtools.common.otio_utils import create_timeline_from_elements, write_timeline_to_fcpxml
from avtools.common.fcpxml_utils import snap_to_frame_grid
from avtools.common.ffmpeg_utils import get_video_info

getcontext().prec = 20

DEFAULT_FRAME_RATE = 50

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

    if output_fcpxml_path is None:
        output_fcpxml_path = input_json_path_obj.with_suffix('.fcpxml')
    else:
        output_fcpxml_path = Path(output_fcpxml_path)

    try:
        with open(input_json_path_obj, encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False

    video_info = None
    try:
        video_path_str = data.get('path')
        if not video_path_str:
            video_path_str = data.get('video_path')  # Also check for video_path key

        if video_path_str and Path(video_path_str).exists():
            print(f"Using path from JSON data: {video_path_str}")
        elif video_path:
            video_path_str = str(video_path)
            print(f"Using provided video path: {video_path_str}")
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
            print("Warning: No video file specified or found. Using default video parameters.")

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
        video_info = {
            'duration': '60',  # Default 60 second duration
            'fps': str(DEFAULT_FRAME_RATE if frame_rate is None else frame_rate),
            'width': '1920',
            'height': '1080'
        }

    return create_fcpxml_from_data(data, video_info, output_fcpxml_path, input_json_path_obj, frame_rate, video_path_str)

def create_fcpxml_from_data(json_data, video_info, output_fcpxml_path, input_json_path_obj, frame_rate=None, video_path_str=None):
    """Creates FCPXML using the otio-fcpx-xml-lite-adapter with frame-aligned markers and video shots."""
    if video_info is None:
        print("Error: Cannot proceed without video information.")
        return False

    if frame_rate is None:
        try:
            frame_rate = float(video_info['fps'])
            print(f"Using detected frame rate from video: {frame_rate}")
        except (KeyError, ValueError):
            frame_rate = DEFAULT_FRAME_RATE
            print(f"Could not determine frame rate from video, using default: {frame_rate}")

    if not video_path_str:
        video_filename = input_json_path_obj.stem + ".mp4"  # Default name based on JSON
        video_path_str = str(Path(video_filename).absolute())
    else:
        video_filename = Path(video_path_str).name

    shots = json_data.get('shots', [])
    if not shots:
        print("Error: No shots found in the JSON data.")
        return False

    asset_native_duration_sec = Decimal(str(video_info['duration']))

    processed_shots = []
    for i, shot in enumerate(shots):
        shot_start_sec = Decimal(str(shot['time_offset']))
        shot_duration_sec = Decimal(str(shot['time_duration']))
        shot_prob = shot.get('probability', 0)

        snapped_start_sec = snap_to_frame_grid(shot_start_sec, frame_rate)
        snapped_end_sec = snap_to_frame_grid(shot_start_sec + shot_duration_sec, frame_rate)

        processed_shots.append({
            'index': i,
            'start_sec': snapped_start_sec,
            'end_sec': snapped_end_sec,
            'prob': shot_prob
        })

    processed_shots.sort(key=lambda x: x['start_sec'])

    max_event_time_sec = max([shot['end_sec'] for shot in processed_shots]) if processed_shots else Decimal('0.0')
    timeline_duration_sec = max(asset_native_duration_sec, max_event_time_sec)
    timeline_duration_sec = snap_to_frame_grid(timeline_duration_sec, frame_rate)

    elements = []

    main_video_clip = {
        "type": "clip",
        "name": video_filename,
        "start_time": 0,
        "duration": float(timeline_duration_sec),
        "source_path": video_path_str,
        "markers": []
    }

    for shot_info in processed_shots:
        shot_start_sec = shot_info['start_sec']
        shot_prob = shot_info['prob']
        shot_index = shot_info['index']

        marker_name = f"Shot {shot_index + 1}"
        marker_note = f"Start: {shot_start_sec}s, Prob: {shot_prob:.2f}"

        main_video_clip["markers"].append({
            "time": float(shot_start_sec),
            "name": marker_name,
            "note": marker_note
        })

    elements.append(main_video_clip)

    for i, shot_info in enumerate(processed_shots):
        shot_start_sec = shot_info['start_sec']
        original_end_sec = shot_info['end_sec']

        if i < len(processed_shots) - 1:
            next_start_sec = processed_shots[i + 1]['start_sec']
            shot_end_sec = next_start_sec
        else:
            shot_end_sec = original_end_sec

        shot_duration_sec = shot_end_sec - shot_start_sec

        elements.append({
            "type": "clip",
            "name": f"Shot {shot_info['index'] + 1}",
            "start_time": float(shot_start_sec),
            "duration": float(shot_duration_sec),
            "source_path": video_path_str,
            "source_start": float(shot_start_sec),
            "markers": [{
                "time": 0,  # Relative to clip start
                "name": f"Shot {shot_info['index'] + 1}",
                "note": "Extracted segment"
            }]
        })

    timeline_name = f"{video_filename}_Shots"
    timeline = create_timeline_from_elements(timeline_name, float(frame_rate), elements)
    return write_timeline_to_fcpxml(timeline, str(output_fcpxml_path))
