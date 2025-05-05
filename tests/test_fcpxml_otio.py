"""
Tests for the FCPXML generation using otio-fcpx-xml-lite-adapter.
"""

import os
import tempfile
from pathlib import Path
import pytest
import json

from avtools.audio.fcpxml_otio import json_to_fcpxml as audio_json_to_fcpxml
from avtools.video.fcpxml_otio import json_to_fcpxml as video_json_to_fcpxml

@pytest.fixture
def audio_json_data():
    return {
        "path": "test_audio.wav",
        "beats": [0.5, 1.0, 1.5, 2.0],
        "downbeats": [0.5, 1.5],
        "segments": [
            {"start": 0.0, "end": 1.0, "label": "Intro"},
            {"start": 1.0, "end": 2.0, "label": "Verse"}
        ]
    }

@pytest.fixture
def video_json_data():
    return {
        "path": "test_video.mp4",
        "shots": [
            {"time_offset": 0.0, "time_duration": 1.0, "probability": 0.95},
            {"time_offset": 1.0, "time_duration": 1.0, "probability": 0.90}
        ]
    }

def test_audio_json_to_fcpxml(audio_json_data, monkeypatch):
    def mock_get_audio_info(path):
        return {"duration": "10.0", "sample_rate": "48000"}
    
    monkeypatch.setattr("avtools.audio.fcpxml_otio.get_audio_info", mock_get_audio_info)
    
    monkeypatch.setattr(Path, "exists", lambda self: True)
    
    with tempfile.NamedTemporaryFile(suffix='.json') as json_file, \
         tempfile.NamedTemporaryFile(suffix='.fcpxml') as fcpxml_file:
        
        with open(json_file.name, 'w') as f:
            json.dump(audio_json_data, f)
        
        result = audio_json_to_fcpxml(json_file.name, fcpxml_file.name, frame_rate=25)
        
        assert result is True
        
        assert os.path.exists(fcpxml_file.name)
        assert os.path.getsize(fcpxml_file.name) > 0
        
        with open(fcpxml_file.name, 'r') as f:
            content = f.read()
            assert '<?xml version="1.0" encoding="UTF-8"?>' in content
            assert '<!DOCTYPE fcpxml>' in content
            assert '<fcpxml ' in content

def test_video_json_to_fcpxml(video_json_data, monkeypatch):
    def mock_get_video_info(path):
        return {"duration": "10.0", "fps": "25.0", "width": "1920", "height": "1080"}
    
    monkeypatch.setattr("avtools.video.fcpxml_otio.get_video_info", mock_get_video_info)
    
    monkeypatch.setattr(Path, "exists", lambda self: True)
    
    with tempfile.NamedTemporaryFile(suffix='.json') as json_file, \
         tempfile.NamedTemporaryFile(suffix='.fcpxml') as fcpxml_file:
        
        with open(json_file.name, 'w') as f:
            json.dump(video_json_data, f)
        
        result = video_json_to_fcpxml(json_file.name, fcpxml_file.name, frame_rate=25)
        
        assert result is True
        
        assert os.path.exists(fcpxml_file.name)
        assert os.path.getsize(fcpxml_file.name) > 0
        
        with open(fcpxml_file.name, 'r') as f:
            content = f.read()
            assert '<?xml version="1.0" encoding="UTF-8"?>' in content
            assert '<!DOCTYPE fcpxml>' in content
            assert '<fcpxml ' in content
