"""
Timeline I/O module for converting between different timeline formats.

This module provides functions for converting between JSON, FCPXML, and OTIO formats.
"""

import json
import os
from decimal import Decimal, getcontext
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import opentimelineio as otio

from avtools.common.fcpxml_utils import snap_to_frame_grid
from avtools.common.ffmpeg_utils import get_audio_info, get_video_info
from avtools.common.otio_utils import create_timeline_from_elements, write_timeline_to_fcpxml

try:
    import pygenometracks.plotTracks as pgt
    import matplotlib.pyplot as plt
    import configparser
    PYGENOMETRACKS_AVAILABLE = True
except ImportError:
    PYGENOMETRACKS_AVAILABLE = False

getcontext().prec = 20

DEFAULT_FRAME_RATE = 50


class TimelineFormat(str, Enum):
    """Supported timeline formats."""
    FCPXML = "fcpxml"
    OTIO = "otio"
    PYGENOMETRACKS = "pygenometracks"


def json_to_timeline(
    input_json_path: str,
    output_path: Optional[str] = None,
    media_path: Optional[str] = None,
    frame_rate: Optional[float] = None,
    format: TimelineFormat = TimelineFormat.FCPXML,
    media_type: Optional[str] = None
) -> bool:
    """
    Convert JSON to timeline format (FCPXML or OTIO).

    Parameters:
    - input_json_path: Path to input JSON file with timeline data
    - output_path: Path to output file (default: input path with appropriate extension)
    - media_path: Path to source media file (optional)
    - frame_rate: Frame rate to use (default: auto-detect from media or 50 fps)
    - format: Output format (FCPXML or OTIO)
    - media_type: Type of media ('video' or 'audio', default: auto-detect)

    Returns:
    - True on success, False on failure
    """
    input_json_path_obj = Path(input_json_path)
    if not input_json_path_obj.is_file():
        print(f"Error: Input JSON file not found: {input_json_path_obj}")
        return False

    if output_path is None:
        if format == TimelineFormat.FCPXML:
            output_path = input_json_path_obj.with_suffix('.fcpxml')
        elif format == TimelineFormat.OTIO:
            output_path = input_json_path_obj.with_suffix('.otio')
        else:  # PYGENOMETRACKS
            output_path = input_json_path_obj.with_suffix('.ini')
    else:
        output_path = Path(output_path)

    try:
        with open(input_json_path_obj, encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False

    if media_type is None:
        if 'shots' in data:
            media_type = 'video'
        elif any(key in data for key in ['beats', 'downbeats']):
            media_type = 'audio'
        else:
            print("Warning: Could not determine media type from JSON. Defaulting to video.")
            media_type = 'video'

    media_info = None
    media_path_str = None

    try:
        path_from_json = data.get('path') or data.get('video_path')
        
        if path_from_json and Path(path_from_json).exists():
            media_path_str = str(Path(path_from_json))
            print(f"Using path from JSON data: {media_path_str}")
        elif media_path:
            media_path_str = str(media_path)
            print(f"Using provided media path: {media_path_str}")
        else:
            media_filename = input_json_path_obj.stem
            media_path_guess = input_json_path_obj.parent / f"{media_filename}.{'mp4' if media_type == 'video' else 'wav'}"
            if media_path_guess.exists():
                media_path_str = str(media_path_guess)
                print(f"Using derived media path: {media_path_str}")

        if media_path_str and Path(media_path_str).exists():
            if media_type == 'video':
                media_info = get_video_info(media_path_str)
            else:  # audio
                media_info = get_audio_info(media_path_str)
        
        if not media_info:
            print("Warning: Could not get media info. Using default parameters.")
            
            if media_type == 'video':
                max_time = 0
                for shot in data.get('shots', []):
                    shot_end = float(shot['time_offset']) + float(shot['time_duration'])
                    max_time = max(max_time, shot_end)
                
                media_info = {
                    'duration': str(max_time + 1),
                    'fps': str(DEFAULT_FRAME_RATE if frame_rate is None else frame_rate),
                    'width': '1920',
                    'height': '1080'
                }
            else:  # audio
                max_time = 0
                if 'beats' in data and data['beats']:
                    max_time = max(float(b) for b in data['beats'])
                if 'segments' in data:
                    for seg in data.get('segments', []):
                        if 'end' in seg:
                            max_time = max(max_time, float(seg['end']))
                
                media_info = {
                    'duration': str(max_time + 1),
                    'sample_rate': '48000'
                }
    except Exception as e:
        print(f"Error determining media info: {e}")
        if media_type == 'video':
            media_info = {
                'duration': '60',  # Default 60 second duration
                'fps': str(DEFAULT_FRAME_RATE if frame_rate is None else frame_rate),
                'width': '1920',
                'height': '1080'
            }
        else:  # audio
            media_info = {
                'duration': '60',  # Default 60 second duration
                'sample_rate': '48000'
            }

    timeline = create_timeline_from_json(
        data, 
        media_info, 
        input_json_path_obj, 
        frame_rate, 
        media_path_str, 
        media_type
    )
    
    if timeline is None:
        return False
    
    if format == TimelineFormat.FCPXML:
        return write_timeline_to_fcpxml(timeline, str(output_path))
    elif format == TimelineFormat.OTIO:
        try:
            otio.adapters.write_to_file(timeline, str(output_path))
            print(f"Successfully wrote OTIO file: {output_path}")
            return True
        except Exception as e:
            print(f"Error writing OTIO file: {e}")
            return False
    else:  # PYGENOMETRACKS
        return timeline_to_pygenometracks(timeline, str(output_path), media_type)


def create_timeline_from_json(
    json_data: Dict, 
    media_info: Dict, 
    input_json_path_obj: Path, 
    frame_rate: Optional[float] = None, 
    media_path_str: Optional[str] = None,
    media_type: str = 'video'
) -> Optional[otio.schema.Timeline]:
    """
    Create an OTIO timeline from JSON data.
    
    Parameters:
    - json_data: JSON data containing timeline information
    - media_info: Dictionary with media information
    - input_json_path_obj: Path object for the input JSON file
    - frame_rate: Frame rate to use (default: auto-detect from media or 50 fps)
    - media_path_str: Path to the media file
    - media_type: Type of media ('video' or 'audio')
    
    Returns:
    - OTIO Timeline object or None on failure
    """
    if media_info is None:
        print("Error: Cannot proceed without media information.")
        return None

    if frame_rate is None:
        try:
            if media_type == 'video':
                frame_rate = float(media_info['fps'])
            else:  # For audio, use default frame rate
                frame_rate = DEFAULT_FRAME_RATE
            print(f"Using frame rate: {frame_rate}")
        except (KeyError, ValueError):
            frame_rate = DEFAULT_FRAME_RATE
            print(f"Could not determine frame rate, using default: {frame_rate}")

    if not media_path_str:
        media_filename = input_json_path_obj.stem + f".{'mp4' if media_type == 'video' else 'wav'}"
        media_path_str = str(Path(media_filename).absolute())
    else:
        media_filename = Path(media_path_str).name

    elements = []
    
    if media_type == 'video':
        return create_video_timeline(json_data, media_info, frame_rate, media_path_str, media_filename)
    else:
        return create_audio_timeline(json_data, media_info, frame_rate, media_path_str, media_filename)


def create_video_timeline(
    json_data: Dict, 
    video_info: Dict, 
    frame_rate: float, 
    video_path_str: str,
    video_filename: str
) -> Optional[otio.schema.Timeline]:
    """
    Create a video timeline from JSON data.
    
    Parameters:
    - json_data: JSON data containing video timeline information
    - video_info: Dictionary with video information
    - frame_rate: Frame rate to use
    - video_path_str: Path to the video file
    - video_filename: Filename of the video
    
    Returns:
    - OTIO Timeline object or None on failure
    """
    shots = json_data.get('shots', [])
    if not shots:
        print("Error: No shots found in the JSON data.")
        return None

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
    return create_timeline_from_elements(timeline_name, float(frame_rate), elements)


def timeline_to_pygenometracks(
    timeline: otio.schema.Timeline,
    output_path: str,
    media_type: str
) -> bool:
    """
    Convert an OTIO timeline to pyGenomeTracks format.
    
    Parameters:
    - timeline: OTIO Timeline object
    - output_path: Path to output INI file for pyGenomeTracks
    - media_type: Type of media ('video' or 'audio')
    
    Returns:
    - True on success, False on failure
    """
    if not PYGENOMETRACKS_AVAILABLE:
        print("Error: pyGenomeTracks is not available. Please install it with 'pip install pygenometracks'.")
        return False
    
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        config = configparser.ConfigParser()
        
        config['spacer'] = {
            'height': '0.5'
        }
        
        config['x-axis'] = {
            'fontsize': '12',
            'where': 'top'
        }
        
        # Process timeline data
        tracks = timeline.tracks
        if not tracks or len(tracks) == 0:
            print("Error: Timeline has no tracks.")
            return False
        
        clips = []
        for track in tracks:
            for item in track.each_child():
                if hasattr(item, "name") and hasattr(item, "source_range"):
                    start_time = item.source_range.start_time.value
                    duration = item.source_range.duration.value
                    end_time = start_time + duration
                    
                    clip_info = {
                        'name': item.name,
                        'start': start_time,
                        'end': end_time
                    }
                    
                    if hasattr(item, "markers") and item.markers:
                        clip_info['markers'] = []
                        for marker in item.markers:
                            marker_time = marker.marked_range.start_time.value
                            clip_info['markers'].append({
                                'time': marker_time,
                                'name': marker.name,
                                'note': marker.metadata.get('note', '')
                            })
                    
                    clips.append(clip_info)
        
        if media_type == 'video':
            track_name = 'Video Shots'
        else:
            track_name = 'Audio Segments'
        
        bed_file = os.path.splitext(output_path)[0] + '.bed'
        with open(bed_file, 'w') as f:
            for i, clip in enumerate(clips):
                f.write(f"timeline\t{int(clip['start'] * 1000)}\t{int(clip['end'] * 1000)}\t{clip['name']}\t{i}\t+\n")
        
        config['bed'] = {
            'file': bed_file,
            'title': track_name,
            'height': '3',
            'color': '#FF0000' if media_type == 'video' else '#0000FF',
            'border_color': 'black',
            'labels': 'true'
        }
        
        markers = []
        for clip in clips:
            if 'markers' in clip:
                for marker in clip['markers']:
                    markers.append({
                        'time': marker['time'],
                        'name': marker['name'],
                        'note': marker['note']
                    })
        
        if markers:
            markers_file = os.path.splitext(output_path)[0] + '_markers.bed'
            with open(markers_file, 'w') as f:
                for i, marker in enumerate(markers):
                    marker_start = int(marker['time'] * 1000)
                    marker_end = marker_start + 10  # Small width for markers
                    f.write(f"timeline\t{marker_start}\t{marker_end}\t{marker['name']}\t{i}\t+\n")
            
            config['bed_markers'] = {
                'file': markers_file,
                'title': 'Markers',
                'height': '1.5',
                'color': '#00FF00',
                'border_color': 'black',
                'labels': 'true',
                'style': 'triangles'
            }
        
        with open(output_path, 'w') as configfile:
            config.write(configfile)
        
        png_file = os.path.splitext(output_path)[0] + '.png'
        
        max_time = 0
        for clip in clips:
            max_time = max(max_time, clip['end'])
        
        region = f"timeline:0-{int(max_time * 1000)}"
        
        tracks_obj = pgt.PlotTracks(output_path, dpi=100)
        fig = plt.figure(figsize=(12, 5))
        tracks_obj.plot(fig, region)
        fig.savefig(png_file)
        plt.close(fig)
        
        print(f"Successfully wrote pyGenomeTracks configuration to: {output_path}")
        print(f"Successfully wrote visualization to: {png_file}")
        print(f"Successfully wrote BED data to: {bed_file}")
        if markers:
            print(f"Successfully wrote markers data to: {markers_file}")
        
        return True
    
    except Exception as e:
        print(f"Error creating pyGenomeTracks visualization: {e}")
        return False


def create_audio_timeline(
    json_data: Dict, 
    audio_info: Dict, 
    frame_rate: float, 
    audio_path_str: str,
    audio_filename: str
) -> Optional[otio.schema.Timeline]:
    """
    Create an audio timeline from JSON data.
    
    Parameters:
    - json_data: JSON data containing audio timeline information
    - audio_info: Dictionary with audio information
    - frame_rate: Frame rate to use
    - audio_path_str: Path to the audio file
    - audio_filename: Filename of the audio
    
    Returns:
    - OTIO Timeline object or None on failure
    """
    import bisect
    
    original_beats = [Decimal(str(b)) for b in json_data.get('beats', [])]
    beats = [snap_to_frame_grid(b, frame_rate) for b in original_beats]

    original_downbeats = [Decimal(str(d)) for d in json_data.get('downbeats', [])]
    downbeats_list = sorted([snap_to_frame_grid(d, frame_rate) for d in original_downbeats])

    segments = json_data.get('segments', [])

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
        "source_path": audio_path_str,
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
    return create_timeline_from_elements(timeline_name, float(frame_rate), elements)
