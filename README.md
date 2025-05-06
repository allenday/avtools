# AVTools

Audio and Video Tools for media processing, including shot detection, FCPXML generation, and audio analysis visualization.

## Installation

This project includes submodules that need special handling during installation.

requires cmake and python3-dev to be installed

### Option 1: Using pip (Recommended)

```bash
pip install .
```

### Option 2: Using the install script

```bash
./install.sh
```

This will automatically install all dependencies with the required `--no-build-isolation` flag.

### Option 3: Manual installation

If you prefer to install manually:

1. Clone the repository with submodules:
   ```bash
   git clone --recurse-submodules https://your-repository-url.git
   ```

2. Install dependencies with the required flag:
   ```bash
   pip install -r requirements.txt --no-build-isolation
   ```

3. Install the transnetv2pt module directly:
   ```bash
   cd transnetv2pt
   pip install -e .
   cd ..
   ```

4. Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Usage

### Command Line Interface

AVTools provides a unified command-line interface for all tools:

```bash
# Get help
avtools --help

# Common tools
avtools common probe video.mp4 --json
avtools common probe audio.wav --type audio
avtools common timeline input.json --format fcpxml --type video
avtools common timeline input.json --format otio --type audio
avtools common timeline input.json --format pygenometracks --type video
avtools common timeline input.bed --format pygenometracks --type bed
avtools common timeline input.bed --format pygenometracks --type bed --markers markers.bed --ini custom.ini

# Audio tools
avtools audio fcpxml input.json -o output.fcpxml --fps 30
avtools audio activations input.json -o visualized.mp4

# Video tools
avtools video fcpxml shots.json -v source.mp4 -o shots.fcpxml
avtools video detect-shots source.mp4 -o shots.json
avtools video extract-shots shots.json source.mp4 -o ./extracted_shots/
avtools video extract-frame-tags frames_dir/ -o frame_tags.json
avtools video extract-shot-tags frame_tags.json -o shot_tags.json

# Frame extraction and caching
avtools video frames extract source.mp4 shots.json --positions start,middle,end
avtools video frames extract-all source.mp4 shots.json --output-dir ./frames/
avtools video cache list
avtools video cache clear --older-than 7
```

### Frame Extraction System

AVTools includes a caching frame extraction system that allows you to extract and store frames from shots:

```bash
# Extract key frames from shots and store in cache (start, middle, end by default)
avtools video cache-frames video.mp4 shots.json

# Extract with custom options
avtools video cache-frames video.mp4 shots.json --positions start,end --format png --quality 100

# Extract all frames from shots to a directory (useful for training data)
avtools video extract-frames-to-dir video.mp4 shots.json --output-dir ./frames/ --frame-interval 0.5

# Manage frame cache
avtools video cache-list
avtools video cache-clear --older-than 30  # Clear frames older than 30 days
```

#### Environment Variables

- `AVTOOLS_CACHE_DIR`: Set a custom cache directory (default: `~/.avtools/cache`)

### Legacy Command Line Scripts

For backward compatibility, individual command-line scripts are also available:

```bash
# Audio tools
audio-json-to-fcpxml input.json -o output.fcpxml --fps 30
audio-activations-to-mp4 input.json -o visualized.mp4

# Video tools
video-json-to-fcpxml shots.json -v source.mp4 -o shots.fcpxml
video-extract-shots shots.json source.mp4 -o ./extracted_shots/

# Frame extraction tools
avtools-extract-frames video.mp4 shots.json
avtools-extract-all-frames video.mp4 shots.json --output-dir ./frames/
avtools-cache-list
avtools-cache-clear
```

### Using as a Library

You can also use AVTools as a Python library:

```python
# Timeline conversion (for both audio and video)
from avtools.common.timeline.io import json_to_timeline, TimelineFormat
# Convert to FCPXML
json_to_timeline("input.json", "output.fcpxml", format=TimelineFormat.FCPXML, media_type="video")
# Convert to OTIO
json_to_timeline("input.json", "output.otio", format=TimelineFormat.OTIO, media_type="audio")
# Convert to pyGenomeTracks (generates visualization PNG and coordinate data)
json_to_timeline("input.json", "output.ini", format=TimelineFormat.PYGENOMETRACKS, media_type="video")

# Video shot extraction
from avtools.video import shots
shots.extract_shots("shots.json", "source.mp4", output_dir="./extracted_shots/")

# Legacy FCPXML generation (still supported)
from avtools.audio import fcpxml
fcpxml.json_to_fcpxml("input.json", "output.fcpxml", frame_rate=30)
from avtools.video import fcpxml
fcpxml.json_to_fcpxml("shots.json", "shots.fcpxml", video_path="source.mp4")

# Frame extraction
from avtools.video import frames
from pathlib import Path

# Extract key frames
result = frames.extract_frames(
    video_path=Path("video.mp4"),
    shots_data=Path("shots.json"),
    extract_positions=["start", "middle", "end"]
)

# Get cached frame paths
from avtools.video import cache
frame_paths = cache.get_frame_paths(video_id="my_video")
```

## Using the transnetv2pt module

To use the transnetv2pt module in your code, import from the wrapper module:

```python
# Instead of this, which may not work:
# from transnetv2pt import predict_video

# Use this instead:
from transnetv2_wrapper import predict_video

# Example usage:
scenes = predict_video("path/to/your/video.mp4")
```

The wrapper module handles all the import paths correctly.
