"""
Common utilities for FCPXML generation used by both audio and video modules.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from decimal import Decimal, ROUND_HALF_UP, getcontext
import math
from pathlib import Path

# Set precision for decimal calculations
getcontext().prec = 20

# Default configuration
DEFAULT_FRAME_RATE = 50
PLACEHOLDER_EFFECT_UID = ".../Generators.localized/Elements.localized/Placeholder.localized/Placeholder.motn"


def snap_to_frame_grid(time_sec, frame_rate):
    """Snaps a time in seconds to the nearest frame boundary."""
    # Convert to frames (rounding to nearest frame)
    frames = round(Decimal(str(time_sec)) * Decimal(str(frame_rate)))
    # Convert back to seconds (perfectly aligned to frame boundaries)
    return Decimal(frames) / Decimal(str(frame_rate))


def seconds_to_timeline_time(seconds, timebase, frame_rate, round_up=True):
    """Converts seconds to frame-aligned FCPXML time."""
    try:
        time_decimal = Decimal(str(seconds))
        
        # Convert seconds to frames
        if round_up:
            frames = math.ceil(time_decimal * Decimal(str(frame_rate)))
        else:
            frames = int((time_decimal * Decimal(str(frame_rate))).to_integral_value(rounding=ROUND_HALF_UP))
        
        # Calculate exactly how many timebase units per frame
        timebase_decimal = Decimal(str(timebase))
        timebase_units_per_frame = timebase_decimal / Decimal(str(frame_rate))
        
        # Convert frames to timebase units - ensure integer result
        timebase_units = int(frames * timebase_units_per_frame)
        
        return f"{timebase_units}/{timebase}s"
    except Exception as e:
        print(f"Warning: Could not convert timeline time {seconds}. Error: {e}")
        return f"0/{timebase}s"


def seconds_to_asset_duration(seconds, sample_rate):
    """Converts seconds to FCPXML asset duration format."""
    try:
        time_decimal = Decimal(str(seconds))
        numerator = (time_decimal * Decimal(sample_rate)).to_integral_value(rounding=ROUND_HALF_UP)
        numerator = max(0, int(numerator))
        return f"{numerator}/{int(sample_rate)}s"
    except Exception as e:
        print(f"Warning: Could not convert asset duration {seconds}. Error: {e}")
        return "0s"


def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    xml_fragment = reparsed.documentElement.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    doctype_declaration = '<!DOCTYPE fcpxml>\n'
    return xml_declaration + doctype_declaration + xml_fragment


def create_base_fcpxml(format_id, format_name, frame_duration, width, height, timebase, 
                       event_name, project_name, total_timeline_duration):
    """
    Creates the base FCPXML structure used by both audio and video modules.
    Returns a tuple of (fcpxml, resources, spine, gap) elements.
    """
    # Create the base FCPXML structure
    fcpxml = ET.Element('fcpxml', version='1.13')
    resources = ET.SubElement(fcpxml, 'resources')
    
    # Format definition
    ET.SubElement(resources, 'format', id=format_id, name=format_name,
                frameDuration=frame_duration, width=str(width), height=str(height),
                colorSpace="1-1-1 (Rec. 709)")
    
    # Placeholder effect for markers
    effect_id_placeholder = "r3"
    ET.SubElement(resources, 'effect', id=effect_id_placeholder, name="Placeholder", 
                uid=PLACEHOLDER_EFFECT_UID)
    
    # Library and event structure
    library = ET.SubElement(fcpxml, 'library')
    event = ET.SubElement(library, 'event', name=event_name)
    project = ET.SubElement(event, 'project', name=project_name)
    
    # Sequence
    sequence = ET.SubElement(project, 'sequence', format=format_id,
                          duration=total_timeline_duration,
                          tcStart="0s", tcFormat="NDF",
                          audioLayout="stereo", audioRate="48k")
    spine = ET.SubElement(sequence, 'spine')
    
    # Main gap element
    gap = ET.SubElement(spine, 'gap', name="Gap", offset="0s", start="0s",
                      duration=total_timeline_duration)
    
    return fcpxml, resources, spine, gap, effect_id_placeholder 