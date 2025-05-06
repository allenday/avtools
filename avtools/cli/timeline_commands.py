"""
Timeline-related commands for the avtools CLI.
"""
import click
from pathlib import Path

from avtools.common.timeline.io import (
    json_to_timeline, 
    bed_to_pygenometracks, 
    TimelineFormat
)


@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('-o', '--output', help='Path for the output file')
@click.option('-m', '--media', help='Path to the source media file (optional)')
@click.option('--fps', type=float, help='Frame rate to use (default: auto-detect)')
@click.option('--format', 'output_format', type=click.Choice(['fcpxml', 'otio', 'pygenometracks']), default='fcpxml',
              help='Output format (default: fcpxml)')
@click.option('--type', 'media_type', type=click.Choice(['auto', 'video', 'audio', 'bed']), default='auto',
              help='Media type (default: auto-detect). Use "bed" for BED file input.')
@click.option('--ini', 'ini_file', type=click.Path(exists=True), 
              help='Path to custom INI file for pyGenomeTracks configuration (only used with pygenometracks format)')
@click.option('--markers', 'markers_file', type=click.Path(exists=True),
              help='Path to BED file with markers (only used with pygenometracks format and bed input type)')
def timeline_convert(input_file, output, media, fps, output_format, media_type, ini_file, markers_file):
    """
    Convert JSON or BED to timeline format (FCPXML, OTIO, or pyGenomeTracks).
    
    This command converts JSON data to FCPXML, OTIO, or pyGenomeTracks format.
    It can process both video and audio timeline data.
    
    The pyGenomeTracks format generates both a visualization PNG and the 
    intermediate coordinate data files used for genomic visualization.
    
    For pyGenomeTracks, you can:
    - Provide a custom INI file with the --ini option
    - Use BED files directly as input with --type bed
    - Specify a separate markers BED file with --markers
    """
    input_path = Path(input_file)
    
    if not output:
        if output_format == 'fcpxml':
            output = input_path.with_suffix('.fcpxml')
        elif output_format == 'otio':
            output = input_path.with_suffix('.otio')
        else:  # pygenometracks
            output = input_path.with_suffix('.ini')
    
    if media_type == 'bed':
        if output_format != 'pygenometracks':
            click.echo("Error: BED input type can only be used with pygenometracks format", err=True)
            exit(1)
        
        success = bed_to_pygenometracks(
            bed_file_path=str(input_path),
            output_path=str(output),
            markers_file_path=markers_file,
            custom_ini_path=ini_file
        )
        
        if success:
            png_file = Path(output).with_suffix('.png')
            click.echo(f"Successfully converted BED file {input_path} to pyGenomeTracks format:")
            click.echo(f"  - Configuration: {output}")
            click.echo(f"  - Visualization: {png_file}")
            if markers_file:
                click.echo(f"  - Markers: {markers_file}")
        else:
            click.echo(f"Failed to convert BED file {input_path} to pyGenomeTracks format", err=True)
            exit(1)
        
        return
    
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
        media_type=media_type,
        custom_ini_path=ini_file
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
