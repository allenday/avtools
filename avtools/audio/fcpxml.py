"""
Audio FCPXML generation module for music and audio analysis data.
"""

import json
import xml.etree.ElementTree as ET
import os
import sys
import bisect
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, getcontext

# Import common utilities
from avtools.common.fcpxml_utils import (
    snap_to_frame_grid, seconds_to_timeline_time, seconds_to_asset_duration,
    prettify_xml, create_base_fcpxml, DEFAULT_FRAME_RATE
)
from avtools.common.ffmpeg_utils import get_audio_info

# Configure decimal precision
getcontext().prec = 20

# Constants
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
        
    # Set output path if not provided
    if output_fcpxml_path is None:
        output_fcpxml_path = input_json_path_obj.with_suffix('.fcpxml')
    else:
        output_fcpxml_path = Path(output_fcpxml_path)
    
    # Set frame rate if not provided
    if frame_rate is None:
        frame_rate = DEFAULT_FRAME_RATE
    print(f"Using frame rate: {frame_rate} fps")
    
    # Load JSON data
    try:
        with open(input_json_path_obj, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False
    
    # Get audio file info
    try:
        audio_path_str = data['path']
        audio_file_to_probe = Path(audio_path_str)
        if not audio_file_to_probe.is_absolute():
            audio_file_to_probe = input_json_path_obj.parent.joinpath(audio_file_to_probe).resolve()
        if not audio_file_to_probe.exists():
            print(f"Error: Audio file path derived from JSON does not exist: {audio_file_to_probe}")
            return False
        # Get audio info using ffmpeg
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
    
    # Create FCPXML
    return create_fcpxml_from_data(data, audio_info, output_fcpxml_path, input_json_path_obj, frame_rate)
    

def create_fcpxml_from_data(json_data, audio_info, output_fcpxml_path, input_json_path_obj, frame_rate):
    """Creates FCPXML v1.13 with frame-aligned markers and placeholders."""
    if audio_info is None:
        print("Error: Cannot proceed without audio information.")
        return False

    # Calculate timebase from frame rate
    timebase = str(frame_rate * 1000)
    marker_frame_duration = f"1/{timebase}s"
    sequence_audio_rate_str = "48k"

    # --- Extract JSON Data ---
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
        audio_uri = audio_path.as_uri()
        print(f"--- Asset URI: {audio_uri} ---")
      
        # --- Snap all time values to frame boundaries ---
        print(f"Snapping all time values to {frame_rate}fps grid...")
      
        # Snap beats to frame boundaries
        original_beats = [Decimal(str(b)) for b in json_data.get('beats', [])]
        beats = [snap_to_frame_grid(b, frame_rate) for b in original_beats]
      
        # Snap downbeats to frame boundaries
        original_downbeats = [Decimal(str(d)) for d in json_data.get('downbeats', [])]
        downbeats_list = sorted([snap_to_frame_grid(d, frame_rate) for d in original_downbeats])
      
        # Get segments and prepare for snapping
        segments = json_data.get('segments', [])
      
    except Exception as e:
        print(f"Error processing JSON data: {e}")
        return False

    # --- Get Asset Info from ffprobe results ---
    asset_native_duration_sec = Decimal(str(audio_info['duration']))
    asset_native_rate = int(audio_info['sample_rate'])
    asset_duration_fcpxml = seconds_to_asset_duration(asset_native_duration_sec, asset_native_rate)

    # --- Adjust Segments & Calculate Max Event Time ---
    adjusted_segments = []
    max_event_time_sec = Decimal('0.0')

    for i, seg in enumerate(segments):
        try:
            # Snap segment start/end times to frame boundaries
            original_start_sec = Decimal(str(seg['start']))
            original_end_sec = Decimal(str(seg['end']))
          
            # Snap these times to the frame grid
            snapped_start_sec = snap_to_frame_grid(original_start_sec, frame_rate)
            snapped_end_sec = snap_to_frame_grid(original_end_sec, frame_rate)
          
            label = seg.get('label', f'Segment {i+1}')
            adjusted_start_sec = snapped_start_sec
        
            if downbeats_list:
                is_on_downbeat = False
                # No need for tolerance when checking exact frame-aligned downbeats
                if adjusted_start_sec in downbeats_list:
                    is_on_downbeat = True
              
                if not is_on_downbeat:
                    # Find the next downbeat
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

    # --- Calculate Frame-Aligned Total Timeline Duration ---
    timeline_duration_sec = max(asset_native_duration_sec, max_event_time_sec)
    # Ensure timeline duration is frame-aligned
    timeline_duration_sec = snap_to_frame_grid(timeline_duration_sec, frame_rate)
    total_timeline_duration_fcpxml = seconds_to_timeline_time(timeline_duration_sec, timebase, frame_rate, round_up=True)
    print(f"Timeline Duration: {timeline_duration_sec}s -> {total_timeline_duration_fcpxml}")

    # --- Build FCPXML Structure (v1.13) ---
    format_id_video = "r1"
    format_name = f"FFVideoFormat1080p{frame_rate}"
    frame_duration = f"1/{frame_rate}s"
    event_name = f"{audio_filename}_Analysis"
    project_name = f"{audio_filename}_Placeholders"
    
    # Create base FCPXML structure
    fcpxml, resources, spine, gap, effect_id_placeholder = create_base_fcpxml(
        format_id=format_id_video,
        format_name=format_name,
        frame_duration=frame_duration,
        width="1920",
        height="1080",
        timebase=timebase,
        event_name=event_name,
        project_name=project_name,
        total_timeline_duration=total_timeline_duration_fcpxml
    )
    
    # Define audio asset
    asset_id_audio = "r2"
    asset = ET.SubElement(resources, 'asset', id=asset_id_audio, name=audio_filename,
                          start="0s", duration=asset_duration_fcpxml,
                          hasAudio="1", audioSources="1", audioChannels="2",
                          audioRate=str(asset_native_rate))
    ET.SubElement(asset, 'media-rep', kind='original-media', src=audio_uri)

    # -- Audio Clip with Beat Markers --
    asset_clip_audio = ET.SubElement(gap, 'asset-clip', name=audio_filename,
                                    ref=asset_id_audio, lane="-1", offset="0s",
                                    duration=total_timeline_duration_fcpxml,
                                    audioRole="dialogue")

    # Add Beat markers to the audio asset-clip
    for i, beat_time in enumerate(beats):
        start_fcpxml = seconds_to_timeline_time(beat_time, timebase, frame_rate, round_up=False)
        ET.SubElement(asset_clip_audio, 'marker', start=start_fcpxml,
                      duration=marker_frame_duration, value=f"Beat {i+1}")

    # Add Downbeat markers to the audio asset-clip
    for i, downbeat_time in enumerate(downbeats_list):
        start_fcpxml = seconds_to_timeline_time(downbeat_time, timebase, frame_rate, round_up=False)
        ET.SubElement(asset_clip_audio, 'marker', start=start_fcpxml,
                      duration=marker_frame_duration, value=f"Downbeat {i+1}", note="Downbeat")

    # -- Placeholder Clips with Downbeat Markers --
    placeholder_clips = []  # Track placeholder clips and their time ranges

    for i, seg_info in enumerate(adjusted_segments):
        seg_start_sec = seg_info['adjusted_start']
        seg_label = seg_info['label']
    
        # Determine end time
        if i + 1 < len(adjusted_segments):
            placeholder_end_sec = adjusted_segments[i+1]['adjusted_start']
        else:
            placeholder_end_sec = timeline_duration_sec
    
        placeholder_end_sec = max(seg_start_sec, placeholder_end_sec)
        placeholder_duration_sec = placeholder_end_sec - seg_start_sec
    
        # Skip zero-duration placeholders
        if placeholder_duration_sec <= Decimal(0.0):
            print(f"Skipping zero duration placeholder for '{seg_label}' at {seg_start_sec}s")
            continue
    
        placeholder_offset_fcpxml = seconds_to_timeline_time(seg_start_sec, timebase, frame_rate, round_up=False)
        placeholder_duration_fcpxml = seconds_to_timeline_time(placeholder_duration_sec, timebase, frame_rate, round_up=True)
    
        print(f"Placeholder '{seg_label}': Offset={placeholder_offset_fcpxml}, Duration={placeholder_duration_fcpxml}")
    
        # Create the placeholder <video> element
        placeholder_clip = ET.SubElement(gap, 'video',
                                        ref=effect_id_placeholder,
                                        lane="1",
                                        offset=placeholder_offset_fcpxml,
                                        name=f"{seg_label}",
                                        start="0s",
                                        duration=placeholder_duration_fcpxml)
    
        # Store placeholder info for downbeat marker attachment
        placeholder_clips.append({
            'element': placeholder_clip,
            'start_sec': seg_start_sec,
            'end_sec': placeholder_end_sec,
            'label': seg_label
        })

    # --- Attach Downbeat Markers to Placeholders ---
    # For each placeholder, add markers for downbeats that fall within its time range
    for placeholder_info in placeholder_clips:
        placeholder_clip = placeholder_info['element']
        placeholder_start = placeholder_info['start_sec']
        placeholder_end = placeholder_info['end_sec']
        placeholder_label = placeholder_info['label']
    
        downbeat_counter = 1  # Counter for downbeats within this placeholder
    
        # Find downbeats that fall within this placeholder's time range
        for i, downbeat_time in enumerate(downbeats_list):
            # Skip downbeats before placeholder start
            if downbeat_time < placeholder_start:
                continue
            
            # Skip downbeats after placeholder end
            if downbeat_time >= placeholder_end:
                break
            
            # Calculate relative position within the placeholder
            relative_position_sec = downbeat_time - placeholder_start
            relative_position_fcpxml = seconds_to_timeline_time(relative_position_sec, timebase, frame_rate, round_up=False)
        
            # Add marker to the placeholder
            ET.SubElement(placeholder_clip, 'marker',
                         start=relative_position_fcpxml,
                         duration=marker_frame_duration,
                         value=f"{placeholder_label} DB {downbeat_counter}")
        
            downbeat_counter += 1
    
        # Report how many downbeats were attached
        if downbeat_counter > 1:  # At least one downbeat was found
            print(f"Attached {downbeat_counter-1} downbeat markers to placeholder '{placeholder_label}'")
        else:
            print(f"No downbeats found within placeholder '{placeholder_label}'")

    # --- Write FCPXML File ---
    xml_string = prettify_xml(fcpxml)
    try:
        with open(output_fcpxml_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        print(f"Successfully created FCPXML v1.13 with {frame_rate}fps-aligned markers: {output_fcpxml_path}")
        return True
    except IOError as e:
        print(f"Error writing FCPXML: {e}")
        return False 