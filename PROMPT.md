# Refactoring Plan for avtools

## Current Structure
- CLI scripts directly in `avtools/audio/` and `avtools/video/` directories
- No clear separation between library code and CLI interfaces
- No proper Python package structure

## Refactoring Goals
1. Create a proper Python package structure
2. Separate library code from CLI interfaces
3. Make the code more maintainable and testable
4. Keep backward compatibility for existing users

## Implemented Structure
```
avtools/
├── pyproject.toml          # Modern Python packaging
├── setup.py                # For backward compatibility
├── README.md               # Updated with new usage
├── LICENSE
├── MANIFEST.in             # Package manifest
├── avtools/
│   ├── __init__.py         # Package initialization
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── audio_commands.py  # CLI for audio tools
│   │   ├── video_commands.py  # CLI for video tools
│   │   ├── extract_frames.py  # CLI for frame extraction
│   │   └── main.py            # Main CLI entry point
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── fcpxml.py          # Core audio FCPXML functionality
│   │   └── activations.py     # Core activations functionality
│   ├── video/
│   │   ├── __init__.py
│   │   ├── fcpxml.py          # Core video FCPXML functionality
│   │   ├── shots.py           # Core shot extraction functionality
│   │   ├── frames.py          # Frame extraction functionality
│   │   ├── cache.py           # Cache management utilities
│   │   └── config.py          # Configuration management
│   └── common/
│       ├── __init__.py
│       ├── fcpxml_utils.py    # Shared FCPXML utilities
│       └── ffmpeg_utils.py    # Shared ffmpeg utilities
└── tests/
    ├── audio/               # Audio module tests
    └── video/               # Video module tests
```

## Completed Refactoring Steps

### 1. Initial Setup
- [x] Create proper package structure with `__init__.py` files
- [x] Create a `common` module for shared utilities
- [x] Setup entry points in `setup.py`

### 2. Refactor Audio Module
- [x] Extract core functionality from `json_to_fcpxml.py` to `audio/fcpxml.py`
- [x] Create stub for `activations_to_mp4.py` in `audio/activations.py`
- [x] Create CLI interface in `cli/audio_commands.py`
- [x] Update imports and references

### 3. Refactor Video Module
- [x] Extract core functionality from `json_to_fcpxml.py` to `video/fcpxml.py`
- [x] Extract core functionality from `extract_shots.py` to `video/shots.py`
- [x] Create CLI interface in `cli/video_commands.py`
- [x] Update imports and references

### 4. Common Utilities
- [x] Extract shared FCPXML utilities to `common/fcpxml_utils.py`
- [x] Extract shared ffmpeg utilities to `common/ffmpeg_utils.py`
- [x] Update imports in both audio and video modules

### 5. Create CLI Entry Points
- [x] Create main CLI entry point in `cli/main.py`
- [x] Setup command group structure (e.g., `avtools audio fcpxml`, `avtools video shots`)
- [x] Configure entry points in `setup.py`

### 6. Documentation and Packaging
- [x] Update README with new usage instructions
- [x] Create `pyproject.toml` for modern Python packaging
- [x] Create `MANIFEST.in` for package distribution
- [ ] Add type hints for better code maintainability (pending)

### 7. Testing
- [ ] Create basic unit tests for core functionality (pending)

### 8. Frame Extraction System
- [x] Create configuration management module (`video/config.py`)
- [x] Implement cache management utilities (`video/cache.py`)
- [x] Implement frame extraction functionality (`video/frames.py`)
- [x] Create CLI interface for frame extraction (`cli/extract_frames.py`)
- [x] Add commands to main CLI (`avtools video extract-frames`, etc.)
- [x] Add dedicated command-line scripts (`avtools-extract-frames`, etc.)
- [x] Update documentation with new usage examples

## Implemented Features: Caching and Frame Extraction System

### Objectives
1. Extract and store frames from videos based on shot detection data
2. Implement a caching system to avoid redundant extraction
3. Provide a clean API for other tools to access these frames
4. Support tagging and analysis workflows

### Cache Structure
```
$CACHE_DIR/frames/{video_id}/frame{frame_number:06d}_shot{shot_number:04d}.jpg
```

Where:
- `$CACHE_DIR` is defined by environment variable `AVTOOLS_CACHE_DIR` (default: `~/.avtools/cache`)
- `{video_id}` is a user-provided identifier or a hash of the video file
- `{frame_number}` is the sequential frame number (6-digit zero-padded)
- `{shot_number}` is the shot index (4-digit zero-padded)

### Implemented Files
```
avtools/
└── video/
    ├── frames.py          # Frame extraction functionality
    ├── cache.py           # Cache management utilities
    └── config.py          # Configuration management
```

### Implemented Cache Management Functions
1. **Init Cache**
   - Create cache directory structure if it doesn't exist
   - Set up configuration

2. **Frame Extraction**
   - Extract specific frames based on shot data
   - Support extracting frames at specific positions (start, middle, end, or all frames)
   - Store in cache with standardized naming

3. **Cache Retrieval**
   - Get paths to cached frames for a given video/shot
   - Check if frames exist in cache
   - Return structured metadata

4. **Cache Management**
   - List cached videos/frames
   - Calculate cache size
   - Clear cache (with options for age-based cleanup)

### CLI Commands Added
- `avtools video extract-frames` - Extract frames from shots
- `avtools video extract-all-frames` - Extract all frames from shots
- `avtools video cache-list` - List cached frames
- `avtools video cache-clear` - Clean up cache

### API Implemented
```python
# Frame extraction
extract_frames(
    video_path: Path,
    shots_data: dict,
    cache_dir: Optional[Path] = None,
    video_id: Optional[str] = None,
    extract_positions: List[str] = ["start", "middle", "end"],
    format_: str = "jpg",
    quality: int = 95
) -> dict

# Batch extraction
extract_all_frames(
    video_path: Path,
    shots_data: dict,
    output_dir: Path,
    min_probability: float = 0.5,
    frame_interval: Optional[float] = None
) -> dict

# Cache management
get_cache_info(cache_dir: Optional[Path] = None) -> dict
clear_cache(
    cache_dir: Optional[Path] = None,
    older_than: Optional[int] = None  # Days
) -> dict
get_frame_paths(
    video_id: str,
    shot_number: Optional[int] = None,
    cache_dir: Optional[Path] = None
) -> List[Path]
```

### Integration with Tagging System
- Frames extracted using this system are available at predictable paths
- Tagging systems can process frames and associate tags with shots
- Tags can be aggregated at shot level for analysis
- Results from tagging can be used to enrich shot metadata

## Remaining Tasks
1. Complete the implementation of `activations_to_mp4` in the `audio/activations.py` module
2. Add type hints to all modules for better code maintainability
3. Create unit tests for all modules
4. Implement more detailed error handling and logging throughout the codebase

## Backward Compatibility
- Legacy command-line scripts are maintained via entry points
- Compatible imports and function signatures maintained
- Both command-line and library usage documented in README 