# avtools

## Installation

This project includes submodules that need special handling during installation.

### Option 1: Using the install script

The easiest way to install dependencies is to use the provided script:

```bash
./install.sh
```

This will automatically install all dependencies with the required `--no-build-isolation` flag.

### Option 2: Manual installation

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

### Option 3: Using setup.py

You can also use the setup.py file:

```bash
python setup.py
```

This will install all dependencies with the correct flags.

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