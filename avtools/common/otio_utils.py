"""
Common utilities for converting between OTIO and FCPXML using the otio-fcpx-xml-lite-adapter.
"""

import opentimelineio as otio
from otio_fcpx_xml_lite_adapter import adapter
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Union

def create_timeline_from_elements(name: str, frame_rate: float, elements: list[dict]) -> otio.schema.Timeline:
    """
    Create an OTIO timeline from a list of elements (clips, gaps, etc.)

    Parameters:
    - name: Name of the timeline
    - frame_rate: Frame rate of the timeline
    - elements: List of element dictionaries with keys:
        - type: "clip", "gap", or "marker"
        - name: Element name
        - start_time: Start time in seconds
        - duration: Duration in seconds
        - source_path: Path to media (for clips)
        - markers: List of marker dictionaries (optional)

    Returns:
    - An OTIO Timeline object
    """
    timeline = otio.schema.Timeline(name=name)
    
    timeline.global_start_time = otio.opentime.RationalTime(0, frame_rate)
    
    stack = otio.schema.Stack()
    timeline.tracks = stack
    
    video_track = otio.schema.Track(name="Video", kind=otio.schema.TrackKind.Video)
    stack.append(video_track)
    
    audio_track = otio.schema.Track(name="Audio", kind=otio.schema.TrackKind.Audio)
    stack.append(audio_track)
    
    for elem in elements:
        elem_type = elem.get("type")
        elem_name = elem.get("name", "Unnamed")
        start_time_sec = elem.get("start_time", 0)
        duration_sec = elem.get("duration", 0)

        start_time = otio.opentime.RationalTime(float(start_time_sec) * frame_rate, frame_rate)
        duration = otio.opentime.RationalTime(float(duration_sec) * frame_rate, frame_rate)

        if elem_type == "clip":
            source_path = elem.get("source_path")
            if source_path:
                media_ref = otio.schema.ExternalReference(target_url=str(Path(source_path).absolute().as_uri()))
            else:
                media_ref = otio.schema.MissingReference()

            clip = otio.schema.Clip(
                name=elem_name,
                media_reference=media_ref,
                source_range=otio.opentime.TimeRange(start_time, duration)
            )

            if "markers" in elem:
                for marker in elem["markers"]:
                    marker_time = otio.opentime.RationalTime(float(marker["time"]) * frame_rate, frame_rate)
                    marker_duration = otio.opentime.RationalTime(1, frame_rate)  # 1 frame duration
                    marker_range = otio.opentime.TimeRange(marker_time, marker_duration)

                    m = otio.schema.Marker(
                        name=marker.get("name", "Marker"),
                        marked_range=marker_range
                    )
                    if "note" in marker:
                        m.metadata["fcp_note"] = marker["note"]
                    clip.markers.append(m)

            target_track = audio_track if elem.get("is_audio", False) else video_track
            target_track.append(clip)

        elif elem_type == "gap":
            gap = otio.schema.Gap(
                source_range=otio.opentime.TimeRange(start_time, duration)
            )

            target_track = audio_track if elem.get("is_audio", False) else video_track
            target_track.append(gap)

    return timeline

def write_timeline_to_fcpxml(timeline: otio.schema.Timeline, output_path: str) -> bool:
    """
    Write an OTIO timeline to an FCPXML file

    Parameters:
    - timeline: OTIO Timeline object
    - output_path: Path to write the FCPXML file

    Returns:
    - True on success, False on failure
    """
    try:
        adapter.write_to_file(timeline, output_path)
        return True
    except Exception as e:
        print(f"Error writing FCPXML: {e}")
        return False
