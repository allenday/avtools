import json
import os
from pathlib import Path

import pytest
import subprocess

TEST_DATA_DIR = Path(__file__).parent.parent.parent / "data"
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
        "path": "test_video.mp4"
    }
    
    with open(TEST_JSON, 'w') as f:
        json.dump(test_data, f)
    
    return TEST_JSON

@pytest.mark.usefixtures("create_test_json")
def test_timeline_convert_pygenometracks(tmp_path):
    """Test running the 'avtools common timeline' command with pyGenomeTracks output."""
    output_ini = tmp_path / "output.ini"
    command = [
        "avtools", "common", "timeline",
        str(TEST_JSON),
        "--format", "pygenometracks",
        "--type", "video",
        "-o", str(output_ini)
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Timeline convert stdout:\n{result.stdout}")
        print(f"Timeline convert stderr:\n{result.stderr}")

        assert output_ini.exists(), "Output INI file was not created"
        
        png_file = output_ini.with_suffix('.png')
        bed_file = output_ini.with_suffix('.bed')
        
        assert bed_file.exists(), "BED coordinate data file was not created"
        
        
        with open(output_ini, 'r') as f:
            content = f.read()
            assert '[bed]' in content, "Missing bed track in INI file"
            assert 'file =' in content, "Missing file path in INI file"
            assert 'title =' in content, "Missing title in INI file"

    except subprocess.CalledProcessError as e:
        print(f"Timeline convert stdout on error:\n{e.stdout}")
        print(f"Timeline convert stderr on error:\n{e.stderr}")
        pytest.fail(f"'timeline' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'timeline' test: {e}")
