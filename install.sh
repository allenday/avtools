#!/bin/bash
set -e

echo "Making sure submodules are initialized..."
git submodule update --init --recursive

echo "Installing dependencies with --no-build-isolation flag..."
pip install -r requirements.txt --no-build-isolation

echo "Setting up the transnetv2pt module properly..."
cd transnetv2pt
pip install -e .
cd ..

# Get the Python bin directory to install scripts
PYTHON_BIN=$(dirname $(which python))

echo "Creating command scripts..."
# Create main avtools command
cat > $PYTHON_BIN/avtools << 'END'
#!/usr/bin/env python
import sys
import os

# Add the parent directory to path so we can import avtools modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avtools.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
END
chmod +x $PYTHON_BIN/avtools

# Create audio-json-to-fcpxml command
cat > $PYTHON_BIN/audio-json-to-fcpxml << 'END'
#!/usr/bin/env python
import sys
import os

# Add the parent directory to path so we can import avtools modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avtools.cli.audio_commands import json_to_fcpxml_main

if __name__ == "__main__":
    sys.exit(json_to_fcpxml_main())
END
chmod +x $PYTHON_BIN/audio-json-to-fcpxml

# Create audio-activations-to-mp4 command
cat > $PYTHON_BIN/audio-activations-to-mp4 << 'END'
#!/usr/bin/env python
import sys
import os

# Add the parent directory to path so we can import avtools modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avtools.cli.audio_commands import activations_to_mp4_main

if __name__ == "__main__":
    sys.exit(activations_to_mp4_main())
END
chmod +x $PYTHON_BIN/audio-activations-to-mp4

# Create video-json-to-fcpxml command
cat > $PYTHON_BIN/video-json-to-fcpxml << 'END'
#!/usr/bin/env python
import sys
import os

# Add the parent directory to path so we can import avtools modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avtools.cli.video_commands import json_to_fcpxml_main

if __name__ == "__main__":
    sys.exit(json_to_fcpxml_main())
END
chmod +x $PYTHON_BIN/video-json-to-fcpxml

# Create video-extract-shots command
cat > $PYTHON_BIN/video-extract-shots << 'END'
#!/usr/bin/env python
import sys
import os

# Add the parent directory to path so we can import avtools modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avtools.cli.video_commands import extract_shots_main

if __name__ == "__main__":
    sys.exit(extract_shots_main())
END
chmod +x $PYTHON_BIN/video-extract-shots

echo "Installation complete! CLI commands available:"
echo "  - avtools"
echo "  - audio-json-to-fcpxml"
echo "  - audio-activations-to-mp4"
echo "  - video-json-to-fcpxml"
echo "  - video-extract-shots" 