"""
Cache management utilities for video frames.
"""

import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any, Union

from .config import get_cache_dir, ensure_cache_dir, get_video_dir, get_video_hash

def get_cache_info(cache_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get information about the cache contents.
    
    Args:
        cache_dir: Optional custom cache directory
        
    Returns:
        Dict: Information about cache contents
    """
    if cache_dir is None:
        cache_dir = get_cache_dir()
    
    frames_dir = cache_dir / "frames"
    if not frames_dir.exists():
        return {
            "cache_dir": str(cache_dir),
            "exists": False,
            "videos": 0,
            "frames": 0,
            "size_bytes": 0,
            "videos_list": []
        }
    
    # Get list of videos in cache
    videos = []
    total_frames = 0
    total_size = 0
    
    for video_dir in frames_dir.iterdir():
        if video_dir.is_dir():
            video_id = video_dir.name
            frames = list(video_dir.glob("frame*.jpg"))
            frame_count = len(frames)
            size = sum(f.stat().st_size for f in frames)
            
            # Get frame info for first and last frames
            shots = set()
            for frame in frames:
                frame_name = frame.name
                if "_shot" in frame_name:
                    shot_num = int(frame_name.split("_shot")[1].split(".")[0])
                    shots.add(shot_num)
            
            video_info = {
                "video_id": video_id,
                "frame_count": frame_count,
                "shot_count": len(shots),
                "size_bytes": size,
                "path": str(video_dir)
            }
            
            videos.append(video_info)
            total_frames += frame_count
            total_size += size
    
    return {
        "cache_dir": str(cache_dir),
        "exists": True,
        "videos": len(videos),
        "frames": total_frames,
        "size_bytes": total_size,
        "size_mb": round(total_size / (1024 * 1024), 2),
        "videos_list": videos
    }

def clear_cache(cache_dir: Optional[Path] = None, older_than: Optional[int] = None) -> Dict[str, Any]:
    """
    Clear cache contents.
    
    Args:
        cache_dir: Optional custom cache directory
        older_than: Optional days threshold (only clear items older than this)
        
    Returns:
        Dict: Information about what was cleared
    """
    if cache_dir is None:
        cache_dir = get_cache_dir()
    
    frames_dir = cache_dir / "frames"
    if not frames_dir.exists():
        return {
            "cleared": False,
            "message": "Cache directory does not exist"
        }
    
    videos_removed = 0
    frames_removed = 0
    
    # If older_than is specified, only remove old items
    if older_than is not None:
        cutoff_time = time.time() - (older_than * 86400)  # Convert days to seconds
        
        for video_dir in frames_dir.iterdir():
            if video_dir.is_dir():
                # Check if directory is older than cutoff
                dir_mtime = video_dir.stat().st_mtime
                if dir_mtime < cutoff_time:
                    frames = list(video_dir.glob("frame*.jpg"))
                    frames_removed += len(frames)
                    shutil.rmtree(video_dir)
                    videos_removed += 1
    else:
        # Remove everything
        for video_dir in frames_dir.iterdir():
            if video_dir.is_dir():
                frames = list(video_dir.glob("frame*.jpg"))
                frames_removed += len(frames)
                shutil.rmtree(video_dir)
                videos_removed += 1
    
    return {
        "cleared": True,
        "videos_removed": videos_removed,
        "frames_removed": frames_removed
    }

def get_frame_paths(
    video_id: str, 
    shot_number: Optional[int] = None,
    cache_dir: Optional[Path] = None
) -> List[Path]:
    """
    Get paths to cached frames for a specific video and optionally a specific shot.
    
    Args:
        video_id: Video identifier (hash or user-provided)
        shot_number: Optional shot number to filter by
        cache_dir: Optional custom cache directory
        
    Returns:
        List[Path]: List of paths to matching frames
    """
    video_dir = get_video_dir(video_id, cache_dir)
    if not video_dir.exists():
        return []
    
    if shot_number is not None:
        # Format shot number with zero padding
        shot_str = f"_shot{shot_number:04d}"
        return sorted(video_dir.glob(f"frame*{shot_str}.jpg"))
    else:
        return sorted(video_dir.glob("frame*.jpg"))

def check_frame_exists(
    video_id: str,
    frame_number: int,
    shot_number: int,
    cache_dir: Optional[Path] = None
) -> bool:
    """
    Check if a specific frame exists in the cache.
    
    Args:
        video_id: Video identifier (hash or user-provided)
        frame_number: Frame number
        shot_number: Shot number
        cache_dir: Optional custom cache directory
        
    Returns:
        bool: True if the frame exists, False otherwise
    """
    video_dir = get_video_dir(video_id, cache_dir)
    frame_path = video_dir / f"frame{frame_number:06d}_shot{shot_number:04d}.jpg"
    return frame_path.exists()

def get_frame_path(
    video_id: str,
    frame_number: int,
    shot_number: int,
    cache_dir: Optional[Path] = None
) -> Path:
    """
    Get the path where a specific frame should be stored.
    
    Args:
        video_id: Video identifier (hash or user-provided)
        frame_number: Frame number
        shot_number: Shot number
        cache_dir: Optional custom cache directory
        
    Returns:
        Path: Path where the frame should be stored
    """
    video_dir = get_video_dir(video_id, cache_dir)
    return video_dir / f"frame{frame_number:06d}_shot{shot_number:04d}.jpg" 