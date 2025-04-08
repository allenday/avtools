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
│   │   └── main.py            # Main CLI entry point
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── fcpxml.py          # Core audio FCPXML functionality
│   │   └── activations.py     # Core activations functionality
│   ├── video/
│   │   ├── __init__.py
│   │   ├── fcpxml.py          # Core video FCPXML functionality
│   │   └── shots.py           # Core shot extraction functionality
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

## Remaining Tasks
1. Complete the implementation of `activations_to_mp4` in the `audio/activations.py` module
2. Add type hints to all modules for better code maintainability
3. Create unit tests for all modules
4. Implement more detailed error handling and logging throughout the codebase

## Backward Compatibility
- Legacy command-line scripts are maintained via entry points
- Compatible imports and function signatures maintained
- Both command-line and library usage documented in README 