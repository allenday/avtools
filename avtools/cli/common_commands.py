"""
Common commands for the avtools CLI.
"""
import json
import sys
from pathlib import Path

import click
import ffmpeg

from avtools.common.ffmpeg_utils import get_video_info, get_audio_info


def probe_main():
    """Entry point for standalone probe command."""
    probe.callback = None  # Remove the callback to use as standalone command
    probe()


@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
@click.option('--type', 'media_type', type=click.Choice(['auto', 'video', 'audio']), 
             default='auto', help='Specify media type (default: auto-detect)')
def probe(input_file, output_json, media_type):
    """
    Probe media files for information.
    
    This command uses ffmpeg to extract information about video and audio files.
    It can output basic information or detailed JSON depending on the options.
    """
    file_path = Path(input_file)
    
    if media_type == 'auto':
        try:
            info = get_video_info(str(file_path))
            if info:
                media_type = 'video'
            else:
                info = get_audio_info(str(file_path))
                if info:
                    media_type = 'audio'
                else:
                    click.echo(f"Error: Could not determine media type for {file_path}", err=True)
                    sys.exit(1)
        except Exception as e:
            click.echo(f"Error probing file: {e}", err=True)
            sys.exit(1)
    elif media_type == 'video':
        info = get_video_info(str(file_path))
        if not info:
            click.echo(f"Error: Could not probe {file_path} as video", err=True)
            sys.exit(1)
    elif media_type == 'audio':
        info = get_audio_info(str(file_path))
        if not info:
            click.echo(f"Error: Could not probe {file_path} as audio", err=True)
            sys.exit(1)
    
    if output_json:
        click.echo(json.dumps(info, indent=2))
    else:
        click.echo(f"File: {file_path}")
        click.echo(f"Type: {media_type}")
        for key, value in info.items():
            click.echo(f"{key}: {value}")
