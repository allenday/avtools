"""
Audio-related commands for the avtools CLI.
"""
import click
from pathlib import Path

from avtools.common.timeline.io import json_to_timeline, TimelineFormat


def json_to_fcpxml_main():
    """Convert JSON to Final Cut Pro XML format for audio."""
    @click.command()
    @click.argument('input_json', type=click.Path(exists=True))
    @click.option('-a', '--audio', help='Path to the source audio file (optional)')
    @click.option('-o', '--output', help='Path for the output FCPXML file')
    @click.option('--fps', type=float, help='Frame rate to use (default: 50 fps)')
    def json_to_fcpxml(input_json, audio, output, fps):
        """Convert JSON to Final Cut Pro XML format for audio."""
        input_path = Path(input_json)
        
        if not output:
            output = input_path.with_suffix('.fcpxml')
        
        success = json_to_timeline(
            input_json_path=str(input_path),
            output_path=str(output),
            media_path=audio,
            frame_rate=fps,
            format=TimelineFormat.FCPXML,
            media_type='audio'
        )
        
        if success:
            click.echo(f"Successfully converted {input_path} to FCPXML format: {output}")
        else:
            click.echo(f"Failed to convert {input_path} to FCPXML format", err=True)
            exit(1)
    
    json_to_fcpxml.callback = None  # Remove the callback to use as standalone command
    json_to_fcpxml()


def activations_main():
    """Process audio activations."""
    pass


def activations_to_mp4_main():
    """Convert audio activations to MP4 format."""
    pass
