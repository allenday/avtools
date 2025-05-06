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
@click.option('--format', 'output_format', type=click.Choice(['fcpxml', 'otio', 'pygenometracks']), default='fcpxml',
              help='Output format (default: fcpxml)')
@click.option('--type', 'media_type', type=click.Choice(['auto', 'video', 'audio']), default='auto',
              help='Media type (default: auto-detect)')
def timeline_convert(input_json, output, media, fps, output_format, media_type):
    """
    Convert JSON to timeline format (FCPXML, OTIO, or pyGenomeTracks).
    
    This command converts JSON data to FCPXML, OTIO, or pyGenomeTracks format.
    It can process both video and audio timeline data.
    
    The pyGenomeTracks format generates both a visualization PNG and the 
    intermediate coordinate data files used for genomic visualization.
    """
    input_path = Path(input_json)
    
    if not output:
        if output_format == 'fcpxml':
            output = input_path.with_suffix('.fcpxml')
        elif output_format == 'otio':
            output = input_path.with_suffix('.otio')
        else:  # pygenometracks
            output = input_path.with_suffix('.ini')
    
    if media_type == 'auto':
        media_type = None
    
    if output_format == 'fcpxml':
        format_enum = TimelineFormat.FCPXML
    elif output_format == 'otio':
        format_enum = TimelineFormat.OTIO
    else:  # pygenometracks
        format_enum = TimelineFormat.PYGENOMETRACKS
    
    success = json_to_timeline(
        input_json_path=str(input_path),
        output_path=str(output),
        media_path=media,
        frame_rate=fps,
        format=format_enum,
        media_type=media_type
    )
    
    if success:
        if output_format == 'pygenometracks':
            png_file = Path(output).with_suffix('.png')
            bed_file = Path(output).with_suffix('.bed')
            click.echo(f"Successfully converted {input_path} to {output_format.upper()} format:")
            click.echo(f"  - Configuration: {output}")
            click.echo(f"  - Visualization: {png_file}")
            click.echo(f"  - Coordinate data: {bed_file}")
        else:
            click.echo(f"Successfully converted {input_path} to {output_format.upper()} format: {output}")
    else:
        click.echo(f"Failed to convert {input_path} to {output_format.upper()} format", err=True)
        exit(1)


def timeline_convert_main():
    """Entry point for standalone timeline convert command."""
    timeline_convert.callback = None  # Remove the callback to use as standalone command
    timeline_convert()
