"""
Main CLI entry point for avtools.
"""
import click

@click.group()
def main():
    """AVTools - Audio and Video Tools for Media Processing.
    
    This tool provides various utilities for processing audio and video files.
    """
    pass

@main.group('common')
def common_group():
    """Common utilities for media processing."""
    pass

@common_group.command('probe')
def common_probe():
    """Probe media files for information."""
    from .common_commands import probe
    probe()

@main.group('video')
def video_group():
    """Video processing commands."""
    pass

@video_group.command('fcpxml')
def video_fcpxml():
    """Convert JSON to Final Cut Pro XML format for video."""
    from .video_commands import json_to_fcpxml_main
    json_to_fcpxml_main()

@video_group.command('detect-shots')
def video_detect_shots():
    """Detect shots in a video file."""
    from .video_commands import detect_shots_main
    detect_shots_main()

@video_group.command('extract-shots')
def video_extract_shots():
    """Extract shots from a video file."""
    from .video_commands import extract_shots_main
    extract_shots_main()

@video_group.group('frames')
def video_frames_group():
    """Frame extraction commands."""
    pass

@video_frames_group.command('extract')
def video_extract_frames():
    """Extract frames from a video file."""
    from .extract_frames import main as extract_frames_main
    extract_frames_main()

@video_frames_group.command('extract-all')
def video_extract_all_frames():
    """Extract all frames from a video file."""
    from .extract_frames import extract_all_frames_main
    extract_all_frames_main()

@video_group.group('cache')
def video_cache_group():
    """Cache management commands."""
    pass

@video_cache_group.command('list')
def video_cache_list():
    """List cached frames."""
    from .extract_frames import cache_list_main
    cache_list_main()

@video_cache_group.command('clear')
def video_cache_clear():
    """Clear cached frames."""
    from .extract_frames import cache_clear_main
    cache_clear_main()

@main.group('audio')
def audio_group():
    """Audio processing commands."""
    pass

@audio_group.command('fcpxml')
def audio_fcpxml():
    """Convert JSON to Final Cut Pro XML format for audio."""
    from .audio_commands import json_to_fcpxml_main
    json_to_fcpxml_main()

@audio_group.command('activations')
def audio_activations():
    """Process audio activations."""
    from .audio_commands import activations_main
    activations_main()

@audio_group.command('activations-to-mp4')
def audio_activations_to_mp4():
    """Convert audio activations to MP4 format."""
    from .audio_commands import activations_to_mp4_main
    activations_to_mp4_main()

if __name__ == "__main__":
    main()
