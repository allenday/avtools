import json
from pathlib import Path

import pytest
import subprocess

TEST_DATA_DIR = Path(__file__).parent.parent.parent / "data"
TEST_VIDEO = TEST_DATA_DIR / "music-video.mp4"

@pytest.fixture(scope="module")
def test_data_exists():
    """Fixture to ensure the test video file exists."""
    if not TEST_VIDEO.is_file():
        pytest.fail(f"Test video not found at {TEST_VIDEO}. Please ensure it exists.")
    return TEST_VIDEO

@pytest.mark.usefixtures("test_data_exists")
def test_probe_cli(tmp_path):
    """Test running the 'avtools common probe' command via CLI."""
    output_json = tmp_path / "probe_output.json"
    command = [
        "avtools", "common", "probe",
        str(TEST_VIDEO),
        "--json"
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Probe stdout:\n{result.stdout}")
        print(f"Probe stderr:\n{result.stderr}")

        try:
            data = json.loads(result.stdout)
            assert isinstance(data, dict), "Output is not a JSON object"
            assert "width" in data, "'width' key missing in output JSON"
            assert "height" in data, "'height' key missing in output JSON"
            assert "duration" in data, "'duration' key missing in output JSON"
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON")

    except subprocess.CalledProcessError as e:
        print(f"Probe stdout on error:\n{e.stdout}")
        print(f"Probe stderr on error:\n{e.stderr}")
        pytest.fail(f"'probe' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'probe' test: {e}")

@pytest.mark.usefixtures("test_data_exists")
def test_probe_cli_with_type(tmp_path):
    """Test running the 'avtools common probe' command with explicit type via CLI."""
    command = [
        "avtools", "common", "probe",
        str(TEST_VIDEO),
        "--type", "video"
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Probe stdout:\n{result.stdout}")
        print(f"Probe stderr:\n{result.stderr}")

        assert "File:" in result.stdout, "Output does not contain 'File:' information"
        assert "Type: video" in result.stdout, "Output does not contain 'Type: video' information"
        assert "width:" in result.stdout.lower(), "Output does not contain width information"
        assert "height:" in result.stdout.lower(), "Output does not contain height information"

    except subprocess.CalledProcessError as e:
        print(f"Probe stdout on error:\n{e.stdout}")
        print(f"Probe stderr on error:\n{e.stderr}")
        pytest.fail(f"'probe' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'probe' test: {e}")
