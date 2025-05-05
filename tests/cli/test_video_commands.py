import json
from pathlib import Path

import pytest
import subprocess

# Define the path to the test data relative to the tests directory
TEST_DATA_DIR = Path(__file__).parent.parent / "data"
TEST_VIDEO = TEST_DATA_DIR / "music-video.mp4"

@pytest.fixture(scope="module")
def test_data_exists():
    """Fixture to ensure the test video file exists."""
    if not TEST_VIDEO.is_file():
        pytest.fail(f"Test video not found at {TEST_VIDEO}. Please ensure it exists.")
    return TEST_VIDEO

@pytest.mark.usefixtures("test_data_exists")
def test_detect_shots_cli(tmp_path, monkeypatch): # Add monkeypatch fixture
    """Test running the 'avtools video detect-shots' command via CLI."""
    # Set environment variable for MPS fallback
    monkeypatch.setenv("PYTORCH_ENABLE_MPS_FALLBACK", "1")

    output_json = tmp_path / "detected_shots.json"
    command = [
        "avtools", "video", "detect-shots",
        str(TEST_VIDEO),
        "-o", str(output_json)
    ]

    try:
        # Run the command
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Detect shots stdout:\n{result.stdout}")
        print(f"Detect shots stderr:\n{result.stderr}")

        # Check if output file was created
        assert output_json.is_file(), f"Output JSON file not created: {output_json}"

        # Check if output file is valid JSON and not empty
        with open(output_json) as f:
            try:
                data = json.load(f)
                assert isinstance(data, dict), "Output is not a JSON object"
                assert "shots" in data, "'shots' key missing in output JSON"
                assert isinstance(data["shots"], list), "'shots' is not a list"
                assert len(data["shots"]) > 0, "No shots detected or recorded in JSON"
            except json.JSONDecodeError:
                pytest.fail(f"Output file is not valid JSON: {output_json}")

    except subprocess.CalledProcessError as e:
        print(f"Detect shots stdout on error:\n{e.stdout}")
        print(f"Detect shots stderr on error:\n{e.stderr}")
        pytest.fail(f"'detect-shots' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'detect-shots' test: {e}")

# Add more tests here for other video commands like extract-shots, cache-frames etc.
   