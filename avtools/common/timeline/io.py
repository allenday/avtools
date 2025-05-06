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
    media_type: Optional[str] = None,
    custom_ini_path: Optional[str] = None
) -> bool:
    """
    Convert JSON to timeline format (FCPXML, OTIO, or pyGenomeTracks).

    Parameters:
    - input_json_path: Path to input JSON file with timeline data
    - output_path: Path to output file (default: input path with appropriate extension)
    - media_path: Path to media file (optional)
    - frame_rate: Frame rate to use (default: auto-detect)
    - format: Output format (FCPXML, OTIO, or pyGenomeTracks)
    - media_type: Type of media ('video' or 'audio', default: auto-detect)
    - custom_ini_path: Path to custom INI file for pyGenomeTracks configuration (optional)

    Returns:
    - True on success, False on failure
    """
    try:
        # Determine output path if not provided
        if not output_path:
            if format == TimelineFormat.FCPXML:
                output_path = os.path.splitext(input_json_path)[0] + '.fcpxml'
            elif format == TimelineFormat.OTIO:
                output_path = os.path.splitext(input_json_path)[0] + '.otio'
            else:  # pyGenomeTracks
                output_path = os.path.splitext(input_json_path)[0] + '.ini'
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Load JSON data
        with open(input_json_path, 'r') as f:
            data = json.load(f)
        
        # Auto-detect media type if not provided
        if not media_type:
            if 'shots' in data or 'segments' in data:
                media_type = 'video'
            elif 'beats' in data or 'activations' in data:
                media_type = 'audio'
            else:
                # Try to infer from file path
                if media_path:
                    try:
                        if get_video_info(media_path):
                            media_type = 'video'
                        elif get_audio_info(media_path):
                            media_type = 'audio'
                    except Exception:
                        pass
        
        # If still not determined, default to video
        if not media_type:
            print("Warning: Could not determine media type, defaulting to 'video'")
            media_type = 'video'
        
        # Create timeline based on media type
        if media_type == 'video':
            timeline = create_video_timeline(data, media_path, frame_rate)
        else:  # audio
            timeline = create_audio_timeline(data, media_path, frame_rate)
        
        # Write timeline to output format
        if format == TimelineFormat.FCPXML:
            write_timeline_to_fcpxml(timeline, output_path)
            print(f"Successfully wrote FCPXML to: {output_path}")
        elif format == TimelineFormat.OTIO:
            otio.adapters.write_to_file(timeline, output_path)
            print(f"Successfully wrote OTIO to: {output_path}")
        else:  # pyGenomeTracks
            if not PYGENOMETRACKS_AVAILABLE:
                print("Error: pyGenomeTracks is not available. Please install it with 'pip install pygenometracks'.")
                return False
            
            timeline_to_pygenometracks(timeline, output_path, media_type, custom_ini_path)
        
        return True
    
    except Exception as e:
        print(f"Error converting JSON to timeline: {e}")
        return False


def create_timeline_from_json(
    json_data: Dict,
    media_path: Optional[str] = None,
    frame_rate: Optional[float] = None,
    media_type: str = 'video'
) -> otio.schema.Timeline:
    """
    Create a timeline from JSON data.
    
    Parameters:
    - json_data: Dictionary containing timeline data
    - media_path: Path to media file (optional)
    - frame_rate: Frame rate to use (optional, will be auto-detected if not provided)
    - media_type: Type of media ('video' or 'audio')
    
    Returns:
    - OTIO Timeline object
    """
    if media_type == 'video':
        return create_video_timeline(json_data, media_path, frame_rate)
    else:  # audio
        return create_audio_timeline(json_data, media_path, frame_rate)


def create_video_timeline(
    json_data: Dict,
    video_path: Optional[str] = None,
    frame_rate: Optional[float] = None
) -> otio.schema.Timeline:
    """
    Create a timeline from video JSON data.
    
    Parameters:
    - json_data: Dictionary containing video timeline data
    - video_path: Path to video file (optional)
    - frame_rate: Frame rate to use (optional, will be auto-detected if not provided)
    
    Returns:
    - OTIO Timeline object
    """
    # Use video path from JSON if not provided
    video_path_str = video_path or json_data.get('path', '')
    
    # Get video info if path is provided
    video_info = None
    if video_path_str:
        try:
            video_info = get_video_info(video_path_str)
        except Exception as e:
            print(f"Warning: Could not get video info: {e}")
    
    # Determine frame rate
    if frame_rate is None:
        if video_info and 'frame_rate' in video_info:
            frame_rate = float(video_info['frame_rate'])
        else:
            frame_rate = DEFAULT_FRAME_RATE
            print(f"Warning: Could not determine frame rate, using default: {frame_rate}")
    
    # Get video filename
    video_filename = os.path.basename(video_path_str) if video_path_str else "Unknown"
    
    # Process shots or segments
    shots = json_data.get('shots', [])
    segments = json_data.get('segments', [])
    
    if not shots and not segments:
        print("Warning: No shots or segments found in JSON data")
    
    # Determine timeline duration
    timeline_duration_sec = Decimal('0.0')
    
    if video_info and 'duration' in video_info:
        timeline_duration_sec = Decimal(str(video_info['duration']))
    
    # Process shots/segments
    elements = []
    
    # Add video as a clip if path is provided
    if video_path_str:
        video_clip = {
            "type": "clip",
            "name": video_filename,
            "start_time": 0,
            "duration": float(timeline_duration_sec),
            "source_path": video_path_str,
            "is_video": True,
            "markers": []
        }
        elements.append(video_clip)
    
    # Process shots
    for i, shot in enumerate(shots):
        shot_start_sec = Decimal(str(shot.get('time_offset', 0)))
        shot_duration_sec = Decimal(str(shot.get('time_duration', 0)))
        shot_end_sec = shot_start_sec + shot_duration_sec
        
        # Snap to frame grid
        shot_start_sec = snap_to_frame_grid(shot_start_sec, frame_rate)
        shot_end_sec = snap_to_frame_grid(shot_end_sec, frame_rate)
        shot_duration_sec = shot_end_sec - shot_start_sec
        
        if shot_duration_sec <= Decimal('0.0'):
            print(f"Warning: Shot {i} has zero or negative duration, skipping")
            continue
        
        timeline_duration_sec = max(timeline_duration_sec, shot_end_sec)
        
        shot_name = shot.get('name', f"Shot {i+1}")
        probability = shot.get('probability', 1.0)
        
        elements.append({
            "type": "clip",
            "name": shot_name,
            "start_time": float(shot_start_sec),
            "duration": float(shot_duration_sec),
            "metadata": {
                "probability": probability
            }
        })
    
    # Process segments
    for i, segment in enumerate(segments):
        seg_start_sec = Decimal(str(segment.get('start', 0)))
        seg_end_sec = Decimal(str(segment.get('end', 0)))
        
        # Snap to frame grid
        seg_start_sec = snap_to_frame_grid(seg_start_sec, frame_rate)
        seg_end_sec = snap_to_frame_grid(seg_end_sec, frame_rate)
        seg_duration_sec = seg_end_sec - seg_start_sec
        
        if seg_duration_sec <= Decimal('0.0'):
            print(f"Warning: Segment {i} has zero or negative duration, skipping")
            continue
        
        timeline_duration_sec = max(timeline_duration_sec, seg_end_sec)
        
        seg_name = segment.get('label', f"Segment {i+1}")
        
        elements.append({
            "type": "clip",
            "name": seg_name,
            "start_time": float(seg_start_sec),
            "duration": float(seg_duration_sec)
        })
    
    # Create timeline
    timeline_name = f"{video_filename}_Timeline"
    return create_timeline_from_elements(timeline_name, float(frame_rate), elements)


def bed_to_pygenometracks(
    bed_file_path: str,
    output_path: str,
    markers_file_path: Optional[str] = None,
    custom_ini_path: Optional[str] = None
) -> bool:
    """
    Convert BED file directly to pyGenomeTracks visualization.
    
    Parameters:
    - bed_file_path: Path to input BED file
    - output_path: Path to output INI file for pyGenomeTracks
    - markers_file_path: Path to BED file with markers (optional)
    - custom_ini_path: Path to custom INI file for pyGenomeTracks configuration (optional)
    
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
        
        # Use custom INI if provided, otherwise create default config
        if custom_ini_path and os.path.exists(custom_ini_path):
            print(f"Using custom INI configuration from: {custom_ini_path}")
            config = configparser.ConfigParser()
            config.read(custom_ini_path)
            
            # Update the bed file path in the config if it exists
            if 'bed' in config:
                config['bed']['file'] = bed_file_path
            else:
                config['bed'] = {
                    'file': bed_file_path,
                    'title': 'Synteny',
                    'height': '3',
                    'color': '#FF0000',
                    'border_color': 'black',
                    'labels': 'true'
                }
            
            # Update markers file path if it exists
            if markers_file_path and 'bed_markers' in config:
                config['bed_markers']['file'] = markers_file_path
            elif markers_file_path:
                config['bed_markers'] = {
                    'file': markers_file_path,
                    'title': 'Markers',
                    'height': '1.5',
                    'color': '#00FF00',
                    'border_color': 'black',
                    'labels': 'true',
                    'style': 'triangles'
                }
        else:
            # Create default configuration
            config = configparser.ConfigParser()
            
            config['spacer'] = {
                'height': '0.5'
            }
            
            config['x-axis'] = {
                'fontsize': '12',
                'where': 'top'
            }
            
            config['bed'] = {
                'file': bed_file_path,
                'title': 'Synteny',
                'height': '3',
                'color': '#FF0000',
                'border_color': 'black',
                'labels': 'true'
            }
            
            if markers_file_path:
                config['bed_markers'] = {
                    'file': markers_file_path,
                    'title': 'Markers',
                    'height': '1.5',
                    'color': '#00FF00',
                    'border_color': 'black',
                    'labels': 'true',
                    'style': 'triangles'
                }
        
        # Write the configuration file
        with open(output_path, 'w') as configfile:
            config.write(configfile)
        
        # Determine the region to visualize
        # Read the BED file to find the maximum coordinate
        max_coord = 0
        chromosome = None
        with open(bed_file_path, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    chrom = parts[0]
                    if chromosome is None:
                        chromosome = chrom
                    end = int(parts[2])
                    max_coord = max(max_coord, end)
        
        if chromosome is None:
            print("Error: Could not determine chromosome from BED file.")
            return False
        
        # Generate the visualization
        png_file = os.path.splitext(output_path)[0] + '.png'
        region = f"{chromosome}:0-{max_coord}"
        
        tracks_obj = pgt.PlotTracks(output_path, dpi=100)
        fig = plt.figure(figsize=(12, 5))
        tracks_obj.plot(fig, region)
        fig.savefig(png_file)
        plt.close(fig)
        
        print(f"Successfully wrote pyGenomeTracks configuration to: {output_path}")
        print(f"Successfully wrote visualization to: {png_file}")
        print(f"Using BED data from: {bed_file_path}")
        if markers_file_path:
            print(f"Using markers data from: {markers_file_path}")
        
        return True
    
    except Exception as e:
        print(f"Error creating pyGenomeTracks visualization from BED file: {e}")
        return False


def timeline_to_pygenometracks(
    timeline: otio.schema.Timeline,
    output_path: str,
    media_type: str,
    custom_ini_path: Optional[str] = None
) -> bool:
    """
    Convert an OTIO timeline to pyGenomeTracks format.
    
    Parameters:
    - timeline: OTIO Timeline object
    - output_path: Path to output INI file for pyGenomeTracks
    - media_type: Type of media ('video' or 'audio')
    - custom_ini_path: Path to custom INI file for pyGenomeTracks configuration (optional)
    
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
        
        # Create BED file for clips
        bed_file = os.path.splitext(output_path)[0] + '.bed'
        with open(bed_file, 'w') as f:
            for i, clip in enumerate(clips):
                f.write(f"timeline\t{int(clip['start'] * 1000)}\t{int(clip['end'] * 1000)}\t{clip['name']}\t{i}\t+\n")
        
        # Extract markers
        markers = []
        for clip in clips:
            if 'markers' in clip:
                for marker in clip['markers']:
                    markers.append({
                        'time': marker['time'],
                        'name': marker['name'],
                        'note': marker['note']
                    })
        
        # Create BED file for markers if any
        markers_file = None
        if markers:
            markers_file = os.path.splitext(output_path)[0] + '_markers.bed'
            with open(markers_file, 'w') as f:
                for i, marker in enumerate(markers):
                    marker_start = int(marker['time'] * 1000)
                    marker_end = marker_start + 10  # Small width for markers
                    f.write(f"timeline\t{marker_start}\t{marker_end}\t{marker['name']}\t{i}\t+\n")
        
        # Use custom INI if provided, otherwise create default config
        if custom_ini_path and os.path.exists(custom_ini_path):
            print(f"Using custom INI configuration from: {custom_ini_path}")
            config = configparser.ConfigParser()
            config.read(custom_ini_path)
            
            # Update the bed file path in the config if it exists
            if 'bed' in config:
                config['bed']['file'] = bed_file
            else:
                config['bed'] = {
                    'file': bed_file,
                    'title': track_name,
                    'height': '3',
                    'color': '#FF0000' if media_type == 'video' else '#0000FF',
                    'border_color': 'black',
                    'labels': 'true'
                }
            
            # Update markers file path if it exists
            if markers_file and 'bed_markers' in config:
                config['bed_markers']['file'] = markers_file
            elif markers_file:
                config['bed_markers'] = {
                    'file': markers_file,
                    'title': 'Markers',
                    'height': '1.5',
                    'color': '#00FF00',
                    'border_color': 'black',
                    'labels': 'true',
                    'style': 'triangles'
                }
        else:
            # Create default configuration
            config = configparser.ConfigParser()
            
            config['spacer'] = {
                'height': '0.5'
            }
            
            config['x-axis'] = {
                'fontsize': '12',
                'where': 'top'
            }
            
            config['bed'] = {
                'file': bed_file,
                'title': track_name,
                'height': '3',
                'color': '#FF0000' if media_type == 'video' else '#0000FF',
                'border_color': 'black',
                'labels': 'true'
            }
            
            if markers_file:
                config['bed_markers'] = {
                    'file': markers_file,
                    'title': 'Markers',
                    'height': '1.5',
                    'color': '#00FF00',
                    'border_color': 'black',
                    'labels': 'true',
                    'style': 'triangles'
                }
        
        # Write the configuration file
        with open(output_path, 'w') as configfile:
            config.write(configfile)
        
        # Generate the visualization
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
        if markers_file:
            print(f"Successfully wrote markers data to: {markers_file}")
        
        return True
    
    except Exception as e:
        print(f"Error creating pyGenomeTracks visualization: {e}")
        return False


def create_audio_timeline(
    json_data: Dict,
    audio_path: Optional[str] = None,
    frame_rate: Optional[float] = None
) -> otio.schema.Timeline:
    """
    Create a timeline from audio JSON data.
    
    Parameters:
    - json_data: Dictionary containing audio timeline data
    - audio_path: Path to audio file (optional)
    - frame_rate: Frame rate to use (optional, will be auto-detected if not provided)
    
    Returns:
    - OTIO Timeline object
    """
    import bisect
    
    # Use audio path from JSON if not provided
    audio_path_str = audio_path or json_data.get('path', '')
    
    # Get audio info if path is provided
    audio_info = None
    if audio_path_str:
        try:
            audio_info = get_audio_info(audio_path_str)
        except Exception as e:
            print(f"Warning: Could not get audio info: {e}")
    
    # Determine frame rate
    if frame_rate is None:
        frame_rate = DEFAULT_FRAME_RATE
        print(f"Warning: Using default frame rate for audio: {frame_rate}")
    
    # Get audio filename
    audio_filename = os.path.basename(audio_path_str) if audio_path_str else "Unknown"
    
    # Process beats and segments
    beats = []
    if 'beats' in json_data:
        for beat in json_data['beats']:
            if isinstance(beat, dict) and 'time' in beat:
                beats.append(Decimal(str(beat['time'])))
            else:
                beats.append(Decimal(str(beat)))
    
    downbeats = []
    if 'downbeats' in json_data:
        for downbeat in json_data['downbeats']:
            if isinstance(downbeat, dict) and 'time' in downbeat:
                downbeats.append(Decimal(str(downbeat['time'])))
            else:
                downbeats.append(Decimal(str(downbeat)))
    
    segments = json_data.get('segments', [])
    
    # Sort beats and downbeats
    beats.sort()
    downbeats.sort()
    
    # Create downbeats list if not provided but beats are available
    if not downbeats and beats and 'tempo' in json_data:
        tempo = Decimal(str(json_data['tempo']))
        beats_per_bar = int(json_data.get('time_signature', '4/4').split('/')[0])
        
        if tempo > 0 and beats_per_bar > 0:
            beat_duration = Decimal('60.0') / tempo
            bar_duration = beat_duration * beats_per_bar
            
            # Find first downbeat
            first_downbeat = beats[0] if beats else Decimal('0.0')
            
            # Generate downbeats
            current_downbeat = first_downbeat
            max_time = beats[-1] if beats else Decimal('0.0')
            
            while current_downbeat <= max_time:
                downbeats.append(current_downbeat)
                current_downbeat += bar_duration
    
    # Sort downbeats again after generation
    downbeats_list = sorted(downbeats)
    
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
