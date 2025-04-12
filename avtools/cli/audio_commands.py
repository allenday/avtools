#!/usr/bin/env python3
"""
Command-line interfaces for audio processing tools.
"""

import argparse
import sys
from pathlib import Path

# Import audio library functions
from avtools.audio import activations, fcpxml


def json_to_fcpxml_main(args=None):
    """CLI entry point for audio JSON to FCPXML conversion."""
    if args is None:
        # Create parser for direct script invocation
        parser = argparse.ArgumentParser(
            description='Convert music analysis JSON to FCPXML v1.13 with frame-aligned markers.'
        )
        parser.add_argument(
            'json_file',
            help='Path to the input JSON file.'
        )
        parser.add_argument(
            '-o', '--output',
            help='Path for the output FCPXML file.'
        )
        parser.add_argument(
            '--fps', type=int, default=50,
            help='Frame rate to use (default: 50)'
        )

        args = parser.parse_args()

    # Convert paths to Path objects
    input_json_path = Path(args.json_file)
    if not input_json_path.is_file():
        print(f"Error: Input JSON file not found: {input_json_path}")
        return 1

    output_fcpxml_path = Path(args.output) if args.output else input_json_path.with_suffix('.fcpxml')
    frame_rate = args.fps

    # Call the library function
    result = fcpxml.json_to_fcpxml(
        input_json_path=input_json_path,
        output_fcpxml_path=output_fcpxml_path,
        frame_rate=frame_rate
    )

    return 0 if result else 1


def activations_to_mp4_main(args=None):
    """CLI entry point for audio activations to MP4 conversion."""
    if args is None:
        # Create parser for direct script invocation
        parser = argparse.ArgumentParser(
            description='Convert audio activation data to MP4 video visualization.'
        )
        parser.add_argument(
            'json_file',
            help='Path to the input JSON file with activation data.'
        )
        parser.add_argument(
            '-o', '--output',
            help='Path for the output MP4 file.'
        )

        args = parser.parse_args()

    # Convert paths to Path objects
    input_json_path = Path(args.json_file)
    if not input_json_path.is_file():
        print(f"Error: Input JSON file not found: {input_json_path}")
        return 1

    output_mp4_path = Path(args.output) if args.output else input_json_path.with_suffix('.mp4')

    # Call the library function
    result = activations.activations_to_mp4(
        input_json_path=input_json_path,
        output_mp4_path=output_mp4_path
    )

    return 0 if result else 1


if __name__ == "__main__":
    # If this script is run directly, determine which function to call
    script_name = Path(sys.argv[0]).name

    if "json_to_fcpxml" in script_name:
        sys.exit(json_to_fcpxml_main())
    elif "activations_to_mp4" in script_name:
        sys.exit(activations_to_mp4_main())
    else:
        print(f"Error: Unknown script name: {script_name}")
        sys.exit(1)
