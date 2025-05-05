from setuptools import setup, find_packages


setup(
    name="avtools",
    version="0.1.0",
    description="Audio and Video Tools for Media Processing",
    author="Allen Day",
    author_email="allenday@allenday.com",
    url="https://github.com/allenday/avtools",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "avtools=avtools.cli.main:main",
            "avtools-video-fcpxml=avtools.cli.video_commands:json_to_fcpxml_main",
            "avtools-video-detect-shots=avtools.cli.video_commands:detect_shots_main",
            "avtools-video-extract-shots=avtools.cli.video_commands:extract_shots_main",
            "avtools-video-extract-frames=avtools.cli.extract_frames:main",
            "avtools-video-extract-all-frames=avtools.cli.extract_frames:extract_all_frames_main",
            "avtools-audio-fcpxml=avtools.cli.audio_commands:json_to_fcpxml_main",
            "avtools-audio-activations=avtools.cli.audio_commands:activations_main",
            # Legacy entry points for backward compatibility
            "audio-json-to-fcpxml=avtools.cli.audio_commands:json_to_fcpxml_main",
            "audio-activations-to-mp4=avtools.cli.audio_commands:activations_to_mp4_main",
            "video-json-to-fcpxml=avtools.cli.video_commands:json_to_fcpxml_main",
            "video-extract-shots=avtools.cli.video_commands:extract_shots_main",
            # New frame extraction and cache management commands
            "avtools-extract-frames=avtools.cli.extract_frames:main",
            "avtools-extract-all-frames=avtools.cli.extract_frames:extract_all_frames_main",
            "avtools-cache-list=avtools.cli.extract_frames:cache_list_main",
            "avtools-cache-clear=avtools.cli.extract_frames:cache_clear_main",
        ],
    },
)
