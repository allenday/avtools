#!/bin/bash
set -e

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project directory: $PROJECT_DIR"

echo "Making sure submodules are initialized..."
git submodule update --init --recursive

echo "Installing/upgrading basic build tools (pip, setuptools, wheel)..."
pip install --upgrade pip setuptools wheel

echo "Installing PyTorch (needed for NATTEN build)..."
pip install torch==2.6.0

echo "Setting up the wd14-tagger-standalone submodule properly..."
cd wd14-tagger-standalone
pip install -e .
cd "$PROJECT_DIR" # Ensure we cd back to project root

echo "Setting up the TransNetV2 submodule properly..."
if [ -d "TransNetV2" ]; then
    cd TransNetV2
    echo "Installing TransNetV2 submodule..."
    pip install -e .
    cd "$PROJECT_DIR" # Ensure we cd back to project root
else
    echo "Error: TransNetV2 directory not found. Submodule update may have failed or path is incorrect."
    exit 1
fi

# Clean up any other Python build artifacts in the project
echo "Cleaning up any Python build artifacts..."
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

echo "Installing the avtools package and all its Python dependencies (including development tools)..."
# This single command should install avtools in editable mode, along with all Python
# dependencies defined in pyproject.toml (including those in [project.optional-dependencies.dev])
# and create all scripts defined in [project.scripts].
# Dependencies like torch, torchvision, torchaudio, allin1, natten, madmom, etc.,
# will be resolved and installed based on pyproject.toml.
pip install -e ".[dev]"

# Get the Python bin directory to install scripts
PYTHON_BIN=$(dirname $(which python))

echo "Creating legacy symlinks..."
# Create legacy symlinks for backward compatibility
ln -sf $PYTHON_BIN/avtools-audio-json-to-fcpxml $PYTHON_BIN/audio-json-to-fcpxml
ln -sf $PYTHON_BIN/avtools-audio-activations-to-mp4 $PYTHON_BIN/audio-activations-to-mp4
ln -sf $PYTHON_BIN/avtools-video-json-to-fcpxml $PYTHON_BIN/video-json-to-fcpxml
ln -sf $PYTHON_BIN/avtools-video-extract-shots $PYTHON_BIN/video-extract-shots

echo "Installation complete!"
echo "To activate the virtual environment, run: source .venv/bin/activate"
echo "Then you can use the 'avtools' command and its subcommands."
