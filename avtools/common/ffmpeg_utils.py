"""
Common ffmpeg utilities for media file processing.
"""

import sys

import ffmpeg


def get_video_info(file_path_str):
    """
    Uses ffmpeg-python to get video file information including:
    - duration
    - frame rate
    - dimensions

    Returns a dictionary with the information or None if there was an error.
    """
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
                    # width_int = int(width) # Removed unused variable F841
                    # height_int = int(height) # Removed unused variable F841

                    if duration_float > 0 and fps_float > 0:
                        print(f"ffmpeg-python: Duration={duration}, FPS={fps}, Dimensions={width}x{height}")
                        return {
                            'duration': str(duration),
                            'fps': str(fps),
                            'width': str(width),
                            'height': str(height)
                        }
                    else:
                        print("ffmpeg-python Error: Invalid duration or FPS")
                        return None
                except ValueError:
                    print("ffmpeg-python Error: Could not convert values to numbers")
                    return None
            else:
                print("ffmpeg-python Error: Required properties missing in video stream.")
                return None
        else:
            print("ffmpeg-python Error: No video stream found in file.")
            return None
    except ffmpeg.Error as e:
        print("ffmpeg-python Error: Probe failed.", file=sys.stderr)
        if e.stderr:
            print(f"ffmpeg stderr:\n{e.stderr.decode('utf-8', errors='ignore')}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during probing: {e}", file=sys.stderr)
        return None


def get_audio_info(file_path_str):
    """
    Uses ffmpeg-python to get audio file information including:
    - duration
    - sample rate

    Returns a dictionary with the information or None if there was an error.
    """
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
                        print("ffmpeg-python Error: Invalid duration or sample rate")
                        return None
                except ValueError:
                    print("ffmpeg-python Error: Could not convert duration/rate to number")
                    return None
            else:
                print("ffmpeg-python Error: Duration or sample_rate missing in audio stream.")
                return None
        else:
            print("ffmpeg-python Error: No audio stream found in file.")
            return None
    except ffmpeg.Error as e:
        print("ffmpeg-python Error: Probe failed.", file=sys.stderr)
        if e.stderr:
            print(f"ffmpeg stderr:\n{e.stderr.decode('utf-8', errors='ignore')}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during probing: {e}", file=sys.stderr)
        return None


def extract_frames(input_path, output_path, time_offset, time_duration, scale=None):
    """
    Extract a segment from a video file

    Parameters:
    - input_path: Path to input video
    - output_path: Path to output video
    - time_offset: Start time in seconds
    - time_duration: Duration in seconds
    - scale: Optional output scale as "width:height"

    Returns:
    - True on success, False on failure
    """
    try:
        stream = ffmpeg.input(str(input_path), ss=time_offset, t=time_duration)

        # Apply scaling if provided
        if scale:
            stream = ffmpeg.filter(stream, 'scale', scale)

        stream = ffmpeg.output(stream, str(output_path))
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        return True
    except ffmpeg.Error as e:
        print(f"Error extracting frames: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error during frame extraction: {e}")
        return False
