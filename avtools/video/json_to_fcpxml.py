import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import argparse
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, getcontext
import math
import sys
import ffmpeg

# --- Configuration ---
DEFAULT_FRAME_RATE = 50
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
        
        # Convert seconds to frames
        if round_up:
            frames = math.ceil(time_decimal * Decimal(str(frame_rate)))
        else:
            frames = int((time_decimal * Decimal(str(frame_rate))).to_integral_value(rounding=ROUND_HALF_UP))
        
        # Calculate exactly how many timebase units per frame
        timebase_decimal = Decimal(str(timebase))
        timebase_units_per_frame = timebase_decimal / Decimal(str(frame_rate))
        
        # Convert frames to timebase units - ensure integer result
        timebase_units = int(frames * timebase_units_per_frame)
        
        return f"{timebase_units}/{timebase}s"
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

# --- Function to get video info using ffmpeg-python ---
def get_video_info_ffmpeg(file_path_str):
    """Uses ffmpeg-python to get video duration, frame rate, and dimensions."""
    try:
        print(f"Probing video file: {file_path_str}")
        probe = ffmpeg.probe(file_path_str)
        video_stream = next((stream for stream in probe.get('streams', [])
                            if stream.get('codec_type') == 'video'), None)
        if video_stream:
            duration = video_stream.get('duration')
            
            # Handle different ways that frame rate can be represented
            fps = None
            r_frame_rate = video_stream.get('r_frame_rate', '')
            if r_frame_rate and '/' in r_frame_rate:
                num, den = map(float, r_frame_rate.split('/'))
                if den != 0:  # Avoid division by zero
                    fps = num / den
            
            if not fps:
                avg_frame_rate = video_stream.get('avg_frame_rate', '')
                if avg_frame_rate and '/' in avg_frame_rate:
                    num, den = map(float, avg_frame_rate.split('/'))
                    if den != 0:  # Avoid division by zero
                        fps = num / den
            
            width = video_stream.get('width')
            height = video_stream.get('height')
            
            if duration and fps and width and height:
                try:
                    duration_float = float(duration)
                    fps_float = float(fps)
                    width_int = int(width)
                    height_int = int(height)
                    
                    if duration_float > 0 and fps_float > 0:
                        print(f"ffmpeg-python: Duration={duration}, FPS={fps}, Dimensions={width}x{height}")
                        return {
                            'duration': str(duration), 
                            'fps': str(fps),
                            'width': str(width),
                            'height': str(height)
                        }
                    else:
                        print(f"ffmpeg-python Error: Invalid duration or FPS")
                        return None
                except ValueError:
                    print(f"ffmpeg-python Error: Could not convert values to numbers")
                    return None
            else:
                print("ffmpeg-python Error: Required properties missing in video stream.")
                return None
        else:
            print("ffmpeg-python Error: No video stream found in file.")
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
def create_fcpxml(json_data, video_info, output_fcpxml_path, input_json_path_obj, frame_rate=None):
    """Creates FCPXML v1.13 with frame-aligned markers and placeholders for video shots."""
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
            frame_duration = f"{int(10000)}/{timebase}s"
    
    # Fixed size for markers (1 frame duration)
    marker_frame_duration = f"1/{timebase}s"
    
    # Get path from video_info or use relative path if not available
    video_path_str = video_info.get('source_path')
    
    if not video_path_str or not Path(video_path_str).exists():
        # Try to get path from path field in JSON data
        video_path_str = json_data.get('path')
        if video_path_str and Path(video_path_str).exists():
            print(f"Using video path from JSON data: {video_path_str}")
        # If still not found, try to derive from JSON file name
        elif input_json_path_obj:
            video_filename = input_json_path_obj.stem  # Use JSON filename as video filename (without extension)
            video_path = input_json_path_obj.parent / f"{video_filename}.mp4"  # Assume MP4 extension
            if video_path.exists():
                video_path_str = str(video_path)
                print(f"Using derived video path: {video_path_str}")
            # If no video path found, use a placeholder path
            else:
                video_filename = "source_video.mp4"
                video_path_str = str(Path(video_filename).resolve())
                print(f"Warning: No video file found. Using placeholder path: {video_path_str}")
    
    # Get video filename from path
    video_filename = Path(video_path_str).name
    
    # Create URI for FCPXML (using absolute path)
    video_uri = Path(video_path_str).absolute().as_uri()
    print(f"--- Asset URI: {video_uri} ---")
      
    # Get shots from the JSON data
    shots = json_data.get('shots', [])
    if not shots:
        print("Error: No shots found in the JSON data.")
        return False
      
    # Extract asset info
    asset_native_duration_sec = Decimal(str(video_info['duration']))
    asset_native_fps = Decimal(str(video_info['fps']))
    asset_duration_fcpxml = seconds_to_asset_duration(asset_native_duration_sec, asset_native_fps)
    
    # Calculate total timeline duration
    # Find the last shot's end time
    max_event_time_sec = max([Decimal(str(shot['time_offset'])) + Decimal(str(shot['time_duration'])) for shot in shots])
    timeline_duration_sec = max(asset_native_duration_sec, max_event_time_sec)
    timeline_duration_sec = snap_to_frame_grid(timeline_duration_sec, frame_rate)
    total_timeline_duration_fcpxml = seconds_to_timeline_time(timeline_duration_sec, timebase, frame_rate, round_up=True)
    print(f"Timeline Duration: {timeline_duration_sec}s -> {total_timeline_duration_fcpxml}")

    # --- Build FCPXML Structure (v1.13) ---
    fcpxml = ET.Element('fcpxml', version='1.13')
    resources = ET.SubElement(fcpxml, 'resources')
    
    # Format definition
    format_id_video = "r1"
    format_name = f"FFVideoFormat{height}p{int(frame_rate) if frame_rate == int(frame_rate) else frame_rate}"
    ET.SubElement(resources, 'format', id=format_id_video, name=format_name,
                  frameDuration=frame_duration, width=str(width), height=str(height),
                  colorSpace="1-1-1 (Rec. 709)")
    
    # Video asset
    asset_id_video = "r2"
    asset = ET.SubElement(resources, 'asset', id=asset_id_video, name=video_filename,
                          start="0s", duration=asset_duration_fcpxml,
                          hasVideo="1", hasAudio="1", audioSources="1", audioChannels="2",
                          format=format_id_video)
    ET.SubElement(asset, 'media-rep', kind='original-media', src=video_uri)
    
    # Placeholder effect for shot markers
    effect_id_placeholder = "r3"
    ET.SubElement(resources, 'effect', id=effect_id_placeholder, name="Placeholder", uid=PLACEHOLDER_EFFECT_UID)
    
    # Library and event structure
    library = ET.SubElement(fcpxml, 'library')
    event_name = f"{video_filename}_Shots"
    event = ET.SubElement(library, 'event', name=event_name)
    project_name = f"{video_filename}_Shots"
    project = ET.SubElement(event, 'project', name=project_name)
    
    # Sequence
    sequence = ET.SubElement(project, 'sequence', format=format_id_video,
                            duration=total_timeline_duration_fcpxml,
                            tcStart="0s", tcFormat="NDF",
                            audioLayout="stereo", audioRate="48k")
    spine = ET.SubElement(sequence, 'spine')
    
    # Create a main gap element that spans the entire timeline
    gap = ET.SubElement(spine, 'gap', name="Gap", offset="0s", start="0s",
                        duration=total_timeline_duration_fcpxml)
    
    # Add the main video asset to lane 2
    asset_clip_video = ET.SubElement(gap, 'asset-clip', name=video_filename,
                                    ref=asset_id_video, lane="2", offset="0s",
                                    duration=total_timeline_duration_fcpxml)
    
    # Add shot markers to the video asset-clip
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
                      note=f"Extracted segment")

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
    parser = argparse.ArgumentParser(description='Convert video shot detection JSON to FCPXML v1.13 with frame-aligned markers.')
    parser.add_argument('json_file', help='Path to the input JSON file with shot data.')
    parser.add_argument('-v', '--video', help='Path to the source video file (optional).')
    parser.add_argument('-o', '--output', help='Path for the output FCPXML file.')
    
    # Frame rate argument with common presets
    frame_rate_group = parser.add_mutually_exclusive_group()
    frame_rate_group.add_argument('--fps', type=float, help=f'Custom frame rate to use (default: auto-detect or {DEFAULT_FRAME_RATE})')
    frame_rate_group.add_argument('--ntsc', action='store_true', help='Use NTSC 29.97 fps')
    frame_rate_group.add_argument('--pal', action='store_true', help='Use PAL 25 fps')
    frame_rate_group.add_argument('--film', action='store_true', help='Use Film 23.976 fps')
    
    args = parser.parse_args()

    input_json_path = Path(args.json_file)
    if not input_json_path.is_file():
        print(f"Error: Input JSON file not found: {input_json_path}")
        sys.exit(1)

    output_fcpxml_path = Path(args.output) if args.output else input_json_path.with_suffix('.fcpxml')
    
    # Determine frame rate from arguments
    frame_rate = None
    if args.ntsc:
        frame_rate = 29.97
        print("Using NTSC 29.97 fps")
    elif args.pal:
        frame_rate = 25
        print("Using PAL 25 fps")
    elif args.film:
        frame_rate = 23.976
        print("Using Film 23.976 fps")
    elif args.fps:
        frame_rate = args.fps
        print(f"Using custom frame rate: {frame_rate} fps")

    # Read JSON data
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)

    # Get video info using ffmpeg-python
    video_info = None
    try:
        # First check if path exists in the JSON data
        video_path_str = data.get('path')
        if video_path_str and Path(video_path_str).exists():
            print(f"Using path from JSON data: {video_path_str}")
        # If not in JSON, use command line argument
        elif args.video:
            video_path_str = args.video
            print(f"Using path from command line: {video_path_str}")
        # Otherwise try to derive from JSON file name
        else:
            video_filename = input_json_path.stem
            video_path = input_json_path.parent / f"{video_filename}.mp4"  # Assume MP4 extension
            if video_path.exists():
                video_path_str = str(video_path)
                print(f"Using derived video path: {video_path_str}")
            else:
                video_path_str = None
        
        if video_path_str and Path(video_path_str).exists():
            video_info = get_video_info_ffmpeg(video_path_str)
        else:
            # Create minimal video info with default values
            print("Warning: No video file specified or found. Using default video parameters.")
            video_info = {
                'duration': str(max([shot['time_offset'] + shot['time_duration'] for shot in data.get('shots', [])]) + 1),
                'fps': str(DEFAULT_FRAME_RATE if frame_rate is None else frame_rate),
                'width': '1920',
                'height': '1080'
            }
    except Exception as e:
        print(f"Error determining video info: {e}")
        # Create minimal video info with default values
        video_info = {
            'duration': str(max([shot['time_offset'] + shot['time_duration'] for shot in data.get('shots', [])]) + 1),
            'fps': str(DEFAULT_FRAME_RATE if frame_rate is None else frame_rate),
            'width': '1920',
            'height': '1080'
        }

    # Create FCPXML
    success = create_fcpxml(data, video_info, output_fcpxml_path, input_json_path, frame_rate)
    if not success:
        sys.exit(1) 