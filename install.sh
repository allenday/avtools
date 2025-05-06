#!/bin/bash
set -e

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project directory: $PROJECT_DIR"

echo "Making sure submodules are initialized..."
git submodule update --init --recursive

echo "Installing build dependencies..."
pip install --upgrade pip setuptools wheel
pip install build

echo "Installing PyTorch (needed for NATTEN build)..."
pip install torch==2.6.0

echo "Setting up the wd14-tagger-standalone module properly..."
cd wd14-tagger-standalone
pip install -e .
cd ..

# Clean up any other Python build artifacts in the project
find . -type d -name "*.egg-info" -exec rm -rf {} +
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

echo "Installing NATTEN with specific commit hash..."
pip install git+https://github.com/SHI-Labs/NATTEN.git@3b54c76185904f3cb59a49fff7bc044e4513d106#egg=natten --no-build-isolation

echo "Installing Cython and madmom dependencies..."
pip install Cython>=0.29.24

echo "Installing madmom and allin1..."
pip install git+https://github.com/CPJKU/madmom.git@0551aa8f48d71a367d92b5d3a347a0cf7cd97cc9#egg=madmom --no-build-isolation
pip install allin1==1.1.0

echo "Installing OTIO dependencies..."
pip install otio-fcpx-xml-lite-adapter==0.1.0 opentimelineio>=0.17.0

echo "Installing the package with all dependencies..."
pip install -e .

# Get the Python bin directory to install scripts
PYTHON_BIN=$(dirname $(which python))

echo "Creating command scripts..."
# Create main avtools command
cat > $PYTHON_BIN/avtools << EOF
#!/usr/bin/env python
import sys
import os

# Add the project directory to path so we can import avtools modules
sys.path.insert(0, "$PROJECT_DIR")

from avtools.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
EOF
chmod +x $PYTHON_BIN/avtools

# Create avtools-audio-json-to-fcpxml command
cat > $PYTHON_BIN/avtools-audio-json-to-fcpxml << EOF
#!/usr/bin/env python
import sys
import os

# Add the project directory to path so we can import avtools modules
sys.path.insert(0, "$PROJECT_DIR")

from avtools.cli.audio_commands import json_to_fcpxml_main

if __name__ == "__main__":
    sys.exit(json_to_fcpxml_main())
EOF
chmod +x $PYTHON_BIN/avtools-audio-json-to-fcpxml

# Create avtools-audio-activations-to-mp4 command
cat > $PYTHON_BIN/avtools-audio-activations-to-mp4 << EOF
#!/usr/bin/env python
import sys
import os

# Add the project directory to path so we can import avtools modules
sys.path.insert(0, "$PROJECT_DIR")

from avtools.cli.audio_commands import activations_to_mp4_main

if __name__ == "__main__":
    sys.exit(activations_to_mp4_main())
EOF
chmod +x $PYTHON_BIN/avtools-audio-activations-to-mp4

# Create avtools-video-json-to-fcpxml command
cat > $PYTHON_BIN/avtools-video-json-to-fcpxml << EOF
#!/usr/bin/env python
import sys
import os

# Add the project directory to path so we can import avtools modules
sys.path.insert(0, "$PROJECT_DIR")

from avtools.cli.video_commands import json_to_fcpxml_main

if __name__ == "__main__":
    sys.exit(json_to_fcpxml_main())
EOF
chmod +x $PYTHON_BIN/avtools-video-json-to-fcpxml

# Create avtools-video-extract-shots command
cat > $PYTHON_BIN/avtools-video-extract-shots << EOF
#!/usr/bin/env python
import sys
import os

# Add the project directory to path so we can import avtools modules
sys.path.insert(0, "$PROJECT_DIR")

from avtools.cli.video_commands import extract_shots_main

if __name__ == "__main__":
    sys.exit(extract_shots_main())
EOF
chmod +x $PYTHON_BIN/avtools-video-extract-shots

# Create avtools-extract-frames command
cat > $PYTHON_BIN/avtools-extract-frames << EOF
#!/usr/bin/env python
import sys
import os

# Add the project directory to path so we can import avtools modules
sys.path.insert(0, "$PROJECT_DIR")

from avtools.cli.extract_frames import main

if __name__ == "__main__":
    sys.exit(main())
EOF
chmod +x $PYTHON_BIN/avtools-extract-frames

# Create avtools-extract-all-frames command
cat > $PYTHON_BIN/avtools-extract-all-frames << EOF
#!/usr/bin/env python
import sys
import os

# Add the project directory to path so we can import avtools modules
sys.path.insert(0, "$PROJECT_DIR")

from avtools.cli.extract_frames import extract_all_frames_main

if __name__ == "__main__":
    sys.exit(extract_all_frames_main())
EOF
chmod +x $PYTHON_BIN/avtools-extract-all-frames

# Create avtools-cache-list command
cat > $PYTHON_BIN/avtools-cache-list << EOF
#!/usr/bin/env python
import sys
import os

# Add the project directory to path so we can import avtools modules
sys.path.insert(0, "$PROJECT_DIR")

from avtools.cli.extract_frames import cache_list_main

if __name__ == "__main__":
    sys.exit(cache_list_main())
EOF
chmod +x $PYTHON_BIN/avtools-cache-list

# Create avtools-cache-clear command
cat > $PYTHON_BIN/avtools-cache-clear << EOF
#!/usr/bin/env python
import sys
import os

# Add the project directory to path so we can import avtools modules
sys.path.insert(0, "$PROJECT_DIR")

from avtools.cli.extract_frames import cache_clear_main

if __name__ == "__main__":
    sys.exit(cache_clear_main())
EOF
chmod +x $PYTHON_BIN/avtools-cache-clear

# Create legacy symlinks for backward compatibility
ln -sf $PYTHON_BIN/avtools-audio-json-to-fcpxml $PYTHON_BIN/audio-json-to-fcpxml
ln -sf $PYTHON_BIN/avtools-audio-activations-to-mp4 $PYTHON_BIN/audio-activations-to-mp4
ln -sf $PYTHON_BIN/avtools-video-json-to-fcpxml $PYTHON_BIN/video-json-to-fcpxml
ln -sf $PYTHON_BIN/avtools-video-extract-shots $PYTHON_BIN/video-extract-shots

echo "Installation complete! CLI commands available:"
echo "  - avtools"
echo "  - avtools-audio-json-to-fcpxml (alias: audio-json-to-fcpxml)"
echo "  - avtools-audio-activations-to-mp4 (alias: audio-activations-to-mp4)"
echo "  - avtools-video-json-to-fcpxml (alias: video-json-to-fcpxml)"
echo "  - avtools-video-extract-shots (alias: video-extract-shots)"
echo "  - avtools-extract-frames"
echo "  - avtools-extract-all-frames"
echo "  - avtools-cache-list"
echo "  - avtools-cache-clear"
