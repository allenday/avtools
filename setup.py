from setuptools import setup, find_packages
import os
import subprocess

def install_requirements():
    """Install requirements with --no-build-isolation flag."""
    subprocess.check_call([
        'pip', 'install', '-r', 'requirements.txt', '--no-build-isolation'
    ])

setup(
    name="avtools",
    version="0.1.0",
    description="Audio and Video Tools for Media Processing",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/avtools",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "ffmpeg-python",
        "numpy",
        "pillow",
    ],
    entry_points={
        "console_scripts": [
            "avtools=avtools.cli.main:main",
            # Legacy entry points for backward compatibility
            "audio-json-to-fcpxml=avtools.cli.audio_commands:json_to_fcpxml_main",
            "audio-activations-to-mp4=avtools.cli.audio_commands:activations_to_mp4_main",
            "video-json-to-fcpxml=avtools.cli.video_commands:json_to_fcpxml_main",
            "video-extract-shots=avtools.cli.video_commands:extract_shots_main",
        ],
    },
)

if __name__ == "__main__":
    # If this script is run directly, install the requirements
    install_requirements()
    # Then install this package
    subprocess.check_call([
        'pip', 'install', '-e', '.', '--no-deps'
    ]) 