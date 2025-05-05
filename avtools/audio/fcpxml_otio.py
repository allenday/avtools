"""
Audio FCPXML generation module using otio-fcpx-xml-lite-adapter.
"""

import bisect
import json
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

import opentimelineio as otio

from avtools.common.otio_utils import create_timeline_from_elements, write_timeline_to_fcpxml
from avtools.common.fcpxml_utils import snap_to_frame_grid
from avtools.common.ffmpeg_utils import get_audio_info

getcontext().prec = 20

DEFAULT_FRAME_RATE = 50
DOWNBEAT_TOLERANCE = Decimal('0.01')

def json_to_fcpxml(input_json_path, output_fcpxml_path=None, frame_rate=None):
    """
    Convert audio analysis JSON to FCPXML with frame-aligned markers.

    Parameters:
    - input_json_path: Path to input JSON file
    - output_fcpxml_path: Path to output FCPXML file (default: input path with .fcpxml extension)
    - frame_rate: Frame rate to use (default: 50 fps)

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

    if frame_rate is None:
        frame_rate = DEFAULT_FRAME_RATE
    print(f"Using frame rate: {frame_rate} fps")

    try:
        with open(input_json_path_obj, encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False

    try:
        audio_path_str = data['path']
        audio_file_to_probe = Path(audio_path_str)
        if not audio_file_to_probe.is_absolute():
            audio_file_to_probe = input_json_path_obj.parent.joinpath(audio_file_to_probe).resolve()
        if not audio_file_to_probe.exists():
            print(f"Error: Audio file path derived from JSON does not exist: {audio_file_to_probe}")
            return False
        audio_info = get_audio_info(str(audio_file_to_probe))
        if not audio_info:
            print("Error: Could not obtain audio info. FCPXML not generated.")
            return False
    except KeyError:
        print("Error: 'path' key missing in JSON file.")
        return False
    except Exception as e:
        print(f"Error resolving audio path or running probe: {e}")
        return False

    return create_fcpxml_from_data(data, audio_info, output_fcpxml_path, input_json_path_obj, frame_rate)

def create_fcpxml_from_data(json_data, audio_info, output_fcpxml_path, input_json_path_obj, frame_rate):
    """Creates FCPXML using the otio-fcpx-xml-lite-adapter with frame-aligned markers."""
    if audio_info is None:
        print("Error: Cannot proceed without audio information.")
        return False

    try:
        audio_path_str = json_data['path']
        audio_path = Path(audio_path_str)
        if not audio_path.is_absolute():
            json_dir = input_json_path_obj.parent
            audio_path = json_dir.joinpath(audio_path_str).resolve()
        if not audio_path.exists():
            print(f"ERROR: Audio file does not exist: {audio_path}")
            return False
        audio_filename = audio_path.name

        print(f"Snapping all time values to {frame_rate}fps grid...")

        original_beats = [Decimal(str(b)) for b in json_data.get('beats', [])]
        beats = [snap_to_frame_grid(b, frame_rate) for b in original_beats]

        original_downbeats = [Decimal(str(d)) for d in json_data.get('downbeats', [])]
        downbeats_list = sorted([snap_to_frame_grid(d, frame_rate) for d in original_downbeats])

        segments = json_data.get('segments', [])

    except Exception as e:
        print(f"Error processing JSON data: {e}")
        return False

    asset_native_duration_sec = Decimal(str(audio_info['duration']))

    adjusted_segments = []
    max_event_time_sec = Decimal('0.0')

    for i, seg in enumerate(segments):
        try:
            original_start_sec = Decimal(str(seg['start']))
            original_end_sec = Decimal(str(seg['end']))

            snapped_start_sec = snap_to_frame_grid(original_start_sec, frame_rate)
            snapped_end_sec = snap_to_frame_grid(original_end_sec, frame_rate)

            label = seg.get('label', f'Segment {i+1}')
            adjusted_start_sec = snapped_start_sec

            if downbeats_list:
                is_on_downbeat = False
                if adjusted_start_sec in downbeats_list:
                    is_on_downbeat = True

                if not is_on_downbeat:
                    next_downbeat_idx = bisect.bisect_left(downbeats_list, adjusted_start_sec)
                    if next_downbeat_idx < len(downbeats_list):
                        adjusted_start_sec = downbeats_list[next_downbeat_idx]
                        print(f"Segment '{label}' start {snapped_start_sec}s adjusted to next downbeat {adjusted_start_sec}s")

            adjusted_segments.append({'adjusted_start': adjusted_start_sec, 'label': label})
            max_event_time_sec = max(max_event_time_sec, snapped_end_sec)
        except Exception as e:
            print(f"Warning: Could not process segment {i}: {seg}. Error: {e}")

    if beats:
        max_event_time_sec = max(max_event_time_sec, max(beats))

    timeline_duration_sec = max(asset_native_duration_sec, max_event_time_sec)
    timeline_duration_sec = snap_to_frame_grid(timeline_duration_sec, frame_rate)

    elements = []

    audio_clip = {
        "type": "clip",
        "name": audio_filename,
        "start_time": 0,
        "duration": float(timeline_duration_sec),
        "source_path": str(audio_path),
        "is_audio": True,
        "markers": []
    }

    for i, beat_time in enumerate(beats):
        audio_clip["markers"].append({
            "time": float(beat_time),
            "name": f"Beat {i+1}"
        })

    for i, downbeat_time in enumerate(downbeats_list):
        audio_clip["markers"].append({
            "time": float(downbeat_time),
            "name": f"Downbeat {i+1}",
            "note": "Downbeat"
        })

    elements.append(audio_clip)

    for i, seg_info in enumerate(adjusted_segments):
        seg_start_sec = seg_info['adjusted_start']
        seg_label = seg_info['label']

        if i + 1 < len(adjusted_segments):
            placeholder_end_sec = adjusted_segments[i+1]['adjusted_start']
        else:
            placeholder_end_sec = timeline_duration_sec

        placeholder_end_sec = max(seg_start_sec, placeholder_end_sec)
        placeholder_duration_sec = placeholder_end_sec - seg_start_sec

        if placeholder_duration_sec <= Decimal('0.0'):
            print(f"Skipping zero duration placeholder for '{seg_label}' at {seg_start_sec}s")
            continue

        elements.append({
            "type": "clip",
            "name": seg_label,
            "start_time": float(seg_start_sec),
            "duration": float(placeholder_duration_sec),
            "is_placeholder": True
        })

    timeline_name = f"{audio_filename}_Analysis"
    timeline = create_timeline_from_elements(timeline_name, float(frame_rate), elements)
    return write_timeline_to_fcpxml(timeline, str(output_fcpxml_path))
