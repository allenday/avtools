import json
import os
from pathlib import Path

import pytest
import subprocess

TEST_DATA_DIR = Path(__file__).parent.parent.parent / "data"
TEST_VIDEO = TEST_DATA_DIR / "music-video.mp4"
TEST_JSON = TEST_DATA_DIR / "test_shots.json"

@pytest.fixture(scope="module")
def create_test_json():
    """Create a test JSON file with shot data."""
    if not TEST_DATA_DIR.exists():
        TEST_DATA_DIR.mkdir(parents=True)
    
    test_data = {
        "shots": [
            {"time_offset": 0.0, "time_duration": 2.5, "probability": 0.95},
            {"time_offset": 2.5, "time_duration": 3.0, "probability": 0.92},
            {"time_offset": 5.5, "time_duration": 4.0, "probability": 0.88}
        ],
        "path": str(TEST_VIDEO)
    }
    
    with open(TEST_JSON, 'w') as f:
        json.dump(test_data, f)
    
    return TEST_JSON

@pytest.mark.usefixtures("create_test_json")
def test_timeline_convert_fcpxml(tmp_path):
    """Test running the 'avtools common timeline' command with FCPXML output."""
    output_fcpxml = tmp_path / "output.fcpxml"
    command = [
        "avtools", "common", "timeline",
        str(TEST_JSON),
        "--format", "fcpxml",
        "--type", "video",
        "-o", str(output_fcpxml)
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Timeline convert stdout:\n{result.stdout}")
        print(f"Timeline convert stderr:\n{result.stderr}")

        assert output_fcpxml.exists(), "Output FCPXML file was not created"
        
        with open(output_fcpxml, 'r') as f:
            content = f.read()
            assert '<?xml version="1.0" encoding="UTF-8"?>' in content, "Missing XML declaration"
            assert '<fcpxml' in content, "Missing fcpxml tag"
            assert '<resources>' in content, "Missing resources tag"
            assert '<asset' in content, "Missing asset tag"

    except subprocess.CalledProcessError as e:
        print(f"Timeline convert stdout on error:\n{e.stdout}")
        print(f"Timeline convert stderr on error:\n{e.stderr}")
        pytest.fail(f"'timeline' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'timeline' test: {e}")

@pytest.mark.usefixtures("create_test_json")
def test_timeline_convert_otio(tmp_path):
    """Test running the 'avtools common timeline' command with OTIO output."""
    output_otio = tmp_path / "output.otio"
    command = [
        "avtools", "common", "timeline",
        str(TEST_JSON),
        "--format", "otio",
        "--type", "video",
        "-o", str(output_otio)
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Timeline convert stdout:\n{result.stdout}")
        print(f"Timeline convert stderr:\n{result.stderr}")

        assert output_otio.exists(), "Output OTIO file was not created"
        
        with open(output_otio, 'r') as f:
            try:
                data = json.load(f)
                assert "OTIO_SCHEMA" in data, "Missing OTIO_SCHEMA in output file"
                assert data.get("OTIO_SCHEMA") == "Timeline.1", "Incorrect OTIO schema"
                assert "tracks" in data, "Missing tracks in OTIO file"
            except json.JSONDecodeError:
                pytest.fail("Output OTIO file is not valid JSON")

    except subprocess.CalledProcessError as e:
        print(f"Timeline convert stdout on error:\n{e.stdout}")
        print(f"Timeline convert stderr on error:\n{e.stderr}")
        pytest.fail(f"'timeline' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'timeline' test: {e}")
