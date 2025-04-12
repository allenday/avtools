"""
Configuration management for video processing cache.
"""
import hashlib
import os
from pathlib import Path
from typing import Any

# Default cache directory
DEFAULT_CACHE_DIR = os.path.expanduser("~/.avtools/cache")

def get_cache_dir() -> Path:
    """
    Get the cache directory from environment variable or default.

    Returns:
        Path: The cache directory path
    """
    cache_dir = os.environ.get("AVTOOLS_CACHE_DIR", DEFAULT_CACHE_DIR)
    return Path(cache_dir)

def ensure_cache_dir(cache_dir: Path | None = None) -> Path:
    """
    Ensure the cache directory exists, creating it if necessary.

    Args:
        cache_dir: Optional custom cache directory

    Returns:
        Path: The cache directory path
    """
    if cache_dir is None:
        cache_dir = get_cache_dir()

    # Create the cache directory if it doesn't exist
    frames_dir = cache_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    return cache_dir

def get_video_hash(video_path: str | Path) -> str:
    """
    Generate a hash for a video file based on its path and modification time.
    This provides a unique identifier without reading the entire file.

    Args:
        video_path: Path to the video file

    Returns:
        str: Hash string identifying the video
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Use path and modification time to create a hash
    file_stat = video_path.stat()
    hash_input = f"{video_path.absolute()}:{file_stat.st_size}:{file_stat.st_mtime}"
    return hashlib.md5(hash_input.encode()).hexdigest()

def get_video_dir(video_id: str, cache_dir: Path | None = None) -> Path:
    """
    Get the directory for a specific video in the cache.

    Args:
        video_id: Video identifier (hash or user-provided)
        cache_dir: Optional custom cache directory

    Returns:
        Path: Path to the video's cache directory
    """
    if cache_dir is None:
        cache_dir = get_cache_dir()

    video_dir = cache_dir / "frames" / video_id
    return video_dir

def get_config() -> dict[str, Any]:
    """
    Get the current configuration settings.

    Returns:
        Dict: Configuration settings
    """
    return {
        "cache_dir": str(get_cache_dir()),
        "default_format": "jpg",
        "default_quality": 95,
        "version": "0.1.0"
    }
