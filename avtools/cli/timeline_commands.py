"""
Timeline-related commands for the avtools CLI.
"""
import click
from pathlib import Path

from avtools.common.timeline.io import json_to_timeline, TimelineFormat


@click.command()
@click.argument('input_json', type=click.Path(exists=True))
@click.option('-o', '--output', help='Path for the output file')
@click.option('-m', '--media', help='Path to the source media file (optional)')
@click.option('--fps', type=float, help='Frame rate to use (default: auto-detect)')
@click.option('--format', 'output_format', type=click.Choice(['fcpxml', 'otio']), default='fcpxml',
              help='Output format (default: fcpxml)')
@click.option('--type', 'media_type', type=click.Choice(['auto', 'video', 'audio']), default='auto',
              help='Media type (default: auto-detect)')
def timeline_convert(input_json, output, media, fps, output_format, media_type):
    """
    Convert JSON to timeline format (FCPXML or OTIO).
    
    This command converts JSON data to either FCPXML or OTIO format.
    It can process both video and audio timeline data.
    """
    input_path = Path(input_json)
    
    if not output:
        if output_format == 'fcpxml':
            output = input_path.with_suffix('.fcpxml')
        else:  # otio
            output = input_path.with_suffix('.otio')
    
    if media_type == 'auto':
        media_type = None
    
    format_enum = TimelineFormat.FCPXML if output_format == 'fcpxml' else TimelineFormat.OTIO
    
    success = json_to_timeline(
        input_json_path=str(input_path),
        output_path=str(output),
        media_path=media,
        frame_rate=fps,
        format=format_enum,
        media_type=media_type
    )
    
    if success:
        click.echo(f"Successfully converted {input_path} to {output_format.upper()} format: {output}")
    else:
        click.echo(f"Failed to convert {input_path} to {output_format.upper()} format", err=True)
        exit(1)


def timeline_convert_main():
    """Entry point for standalone timeline convert command."""
    timeline_convert.callback = None  # Remove the callback to use as standalone command
    timeline_convert()
