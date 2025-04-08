import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import argparse
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, getcontext
import math
import bisect
import sys
import ffmpeg

# --- Configuration ---
DEFAULT_FRAME_RATE = 50
DOWNBEAT_TOLERANCE = Decimal('0.01')
PLACEHOLDER_EFFECT_UID = ".../Generators.localized/Elements.localized/Placeholder.localized/Placeholder.motn"

getcontext().prec = 20

# --- Helper Functions ---
def snap_to_frame_grid(time_sec, frame_rate):
    """Snaps a time in seconds to the nearest frame boundary."""
    # Convert to frames (rounding to nearest frame)
    frames = round(Decimal(str(time_sec)) * Decimal(str(frame_rate)))
    # Convert back to seconds (perfectly aligned to frame boundaries)
    return Decimal(frames) / Decimal(str(frame_rate))

def seconds_to_timeline_time(seconds, timebase, frame_rate, round_up=True):
    """Converts seconds to frame-aligned FCPXML time."""
    try:
        time_decimal = Decimal(str(seconds))
        if round_up:
            total_frames = math.ceil(time_decimal * Decimal(frame_rate))
        else:
            total_frames = (time_decimal * Decimal(frame_rate)).to_integral_value(rounding=ROUND_HALF_UP)
      
        frame_duration_in_tb = Decimal(timebase) / Decimal(frame_rate)
        numerator = total_frames * frame_duration_in_tb
        numerator = int(numerator.to_integral_value(rounding=ROUND_HALF_UP))
        numerator = max(0, numerator)
        return f"{numerator}/{timebase}s"
    except Exception as e:
        print(f"Warning: Could not convert timeline time {seconds}. Error: {e}")
        return f"0/{timebase}s"

def seconds_to_asset_duration(seconds, sample_rate):
    """Converts seconds to FCPXML asset duration format."""
    try:
        time_decimal = Decimal(str(seconds))
        numerator = (time_decimal * Decimal(sample_rate)).to_integral_value(rounding=ROUND_HALF_UP)
        numerator = max(0, int(numerator))
        return f"{numerator}/{int(sample_rate)}s"
    except Exception as e:
        print(f"Warning: Could not convert asset duration {seconds}. Error: {e}")
        return "0s"

def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    xml_fragment = reparsed.documentElement.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    doctype_declaration = '<!DOCTYPE fcpxml>\n'
    return xml_declaration + doctype_declaration + xml_fragment

# --- Function to get audio info using ffmpeg-python ---
def get_audio_info_ffmpeg(file_path_str):
    """Uses ffmpeg-python to get audio duration and sample rate."""
    try:
        print(f"Probing audio file: {file_path_str}")
        probe = ffmpeg.probe(file_path_str)
        audio_stream = next((stream for stream in probe.get('streams', [])
                            if stream.get('codec_type') == 'audio'), None)
        if audio_stream:
            duration = audio_stream.get('duration')
            sample_rate = audio_stream.get('sample_rate')
            if duration and sample_rate:
                try:
                    duration_float = float(duration)
                    sample_rate_int = int(sample_rate)
                    if duration_float > 0 and sample_rate_int > 0:
                        print(f"ffmpeg-python: Duration={duration}, Rate={sample_rate}")
                        return {'duration': str(duration), 'sample_rate': str(sample_rate)}
                    else:
                        print(f"ffmpeg-python Error: Invalid duration or sample rate")
                        return None
                except ValueError:
                    print(f"ffmpeg-python Error: Could not convert duration/rate to number")
                    return None
            else:
                print("ffmpeg-python Error: Duration or sample_rate missing in audio stream.")
                return None
        else:
            print("ffmpeg-python Error: No audio stream found in file.")
            return None
    except ffmpeg.Error as e:
        print(f"ffmpeg-python Error: Probe failed.", file=sys.stderr)
        if e.stderr:
            print(f"ffmpeg stderr:\n{e.stderr.decode('utf-8', errors='ignore')}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during probing: {e}", file=sys.stderr)
        return None

# --- Main FCPXML Creation Logic ---
def create_fcpxml(json_data, audio_info, output_fcpxml_path, input_json_path_obj, frame_rate):
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
    fcpxml = ET.Element('fcpxml', version='1.13')
    resources = ET.SubElement(fcpxml, 'resources')
    format_id_video = "r1"
    ET.SubElement(resources, 'format', id=format_id_video, name=f"FFVideoFormat1080p{frame_rate}",
                  frameDuration=f"1/{frame_rate}s", width="1920", height="1080",
                  colorSpace="1-1-1 (Rec. 709)")
    asset_id_audio = "r2"
    asset = ET.SubElement(resources, 'asset', id=asset_id_audio, name=audio_filename,
                          start="0s", duration=asset_duration_fcpxml,
                          hasAudio="1", audioSources="1", audioChannels="2",
                          audioRate=str(asset_native_rate))
    ET.SubElement(asset, 'media-rep', kind='original-media', src=audio_uri)
    effect_id_placeholder = "r3"
    ET.SubElement(resources, 'effect', id=effect_id_placeholder, name="Placeholder", uid=PLACEHOLDER_EFFECT_UID)
    library = ET.SubElement(fcpxml, 'library')
    event_name = f"{audio_filename}_Analysis"
    event = ET.SubElement(library, 'event', name=event_name)
    project_name = f"{audio_filename}_Placeholders"
    project = ET.SubElement(event, 'project', name=project_name)
    sequence = ET.SubElement(project, 'sequence', format=format_id_video,
                             duration=total_timeline_duration_fcpxml,
                             tcStart="0s", tcFormat="NDF",
                             audioLayout="stereo", audioRate=sequence_audio_rate_str)
    spine = ET.SubElement(sequence, 'spine')
    gap = ET.SubElement(spine, 'gap', name="Gap", offset="0s", start="0s",
                        duration=total_timeline_duration_fcpxml)

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

# --- Command Line Argument Parsing and Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert music analysis JSON to FCPXML v1.13 with frame-aligned markers.')
    parser.add_argument('json_file', help='Path to the input JSON file.')
    parser.add_argument('-o', '--output', help='Path for the output FCPXML file.')
    parser.add_argument('--fps', type=int, default=DEFAULT_FRAME_RATE,
                       help=f'Frame rate to use (default: {DEFAULT_FRAME_RATE})')
    args = parser.parse_args()

    input_json_path = Path(args.json_file)
    if not input_json_path.is_file():
        print(f"Error: Input JSON file not found: {input_json_path}")
        sys.exit(1)

    output_fcpxml_path = Path(args.output) if args.output else input_json_path.with_suffix('.fcpxml')
    frame_rate = args.fps
    print(f"Using frame rate: {frame_rate} fps")

    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)

    audio_info = None
    try:
        audio_path_str = data['path']
        audio_file_to_probe = Path(audio_path_str)
        if not audio_file_to_probe.is_absolute():
             audio_file_to_probe = input_json_path.parent.joinpath(audio_file_to_probe).resolve()
        if not audio_file_to_probe.exists():
             print(f"Error: Audio file path derived from JSON does not exist: {audio_file_to_probe}")
             sys.exit(1)
        # --- Get Audio Info using ffmpeg-python ---
        audio_info = get_audio_info_ffmpeg(str(audio_file_to_probe))

    except KeyError:
        print("Error: 'path' key missing in JSON file.")
        sys.exit(1)
    except Exception as e:
        print(f"Error resolving audio path or running probe: {e}")
        sys.exit(1)

    # --- Create FCPXML ---
    if audio_info:
        success = create_fcpxml(data, audio_info, output_fcpxml_path, input_json_path, frame_rate)
        if not success:
            sys.exit(1)
    else:
        print("Error: Could not obtain audio info via ffmpeg-python. FCPXML not generated.")
        sys.exit(1)
