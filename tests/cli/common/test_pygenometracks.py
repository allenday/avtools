import json
import os
from pathlib import Path
import configparser

import pytest
import subprocess

from avtools.common.timeline.io import (
    timeline_to_pygenometracks,
    bed_to_pygenometracks,
    TimelineFormat
)

TEST_DATA_DIR = Path(__file__).parent.parent.parent / "data"
TEST_JSON = TEST_DATA_DIR / "test_shots.json"
TEST_BED_FILE = TEST_DATA_DIR / "test_synteny.bed"
TEST_MARKERS_FILE = TEST_DATA_DIR / "test_markers.bed"
TEST_INI_FILE = TEST_DATA_DIR / "test_config.ini"
TEST_AUDIO_JSON = TEST_DATA_DIR / "test_audio.json"

@pytest.fixture(scope="module")
def create_test_files():
    """Create test files for pyGenomeTracks tests."""
    if not TEST_DATA_DIR.exists():
        TEST_DATA_DIR.mkdir(parents=True)
    
    video_test_data = {
        "shots": [
            {"time_offset": 0.0, "time_duration": 2.5, "probability": 0.95},
            {"time_offset": 2.5, "time_duration": 3.0, "probability": 0.92},
            {"time_offset": 5.5, "time_duration": 4.0, "probability": 0.88}
        ],
        "path": "test_video.mp4"
    }
    
    with open(TEST_JSON, 'w') as f:
        json.dump(video_test_data, f)
    
    audio_test_data = {
        "beats": [
            {"time_offset": 0.0, "time_duration": 0.5, "confidence": 0.95},
            {"time_offset": 0.5, "time_duration": 0.5, "confidence": 0.92},
            {"time_offset": 1.0, "time_duration": 0.5, "confidence": 0.88}
        ],
        "path": "test_audio.wav"
    }
    
    with open(TEST_AUDIO_JSON, 'w') as f:
        json.dump(audio_test_data, f)
    
    with open(TEST_BED_FILE, 'w') as f:
        f.write("chr1\t1000\t2000\tFeature1\t1\t+\n")
        f.write("chr1\t3000\t5000\tFeature2\t2\t+\n")
        f.write("chr1\t7000\t9000\tFeature3\t3\t+\n")
    
    with open(TEST_MARKERS_FILE, 'w') as f:
        f.write("chr1\t1500\t1510\tMarker1\t1\t+\n")
        f.write("chr1\t4000\t4010\tMarker2\t2\t+\n")
        f.write("chr1\t8000\t8010\tMarker3\t3\t+\n")
    
    with open(TEST_INI_FILE, 'w') as f:
        f.write("[spacer]\n")
        f.write("height = 0.5\n\n")
        f.write("[x-axis]\n")
        f.write("fontsize = 14\n")
        f.write("where = top\n\n")
        f.write("[bed]\n")
        f.write("title = Custom Synteny Track\n")
        f.write("height = 4\n")
        f.write("color = #0000FF\n")
        f.write("border_color = black\n")
        f.write("labels = true\n\n")
        f.write("[bed_markers]\n")
        f.write("title = Custom Markers\n")
        f.write("height = 2\n")
        f.write("color = #FF00FF\n")
        f.write("border_color = black\n")
        f.write("labels = true\n")
        f.write("style = triangles\n")
    
    return TEST_JSON, TEST_AUDIO_JSON, TEST_BED_FILE, TEST_MARKERS_FILE, TEST_INI_FILE

def test_timeline_to_pygenometracks_unit(tmp_path, create_test_files):
    """Unit test for timeline_to_pygenometracks function."""
    output_ini = tmp_path / "unit_test.ini"
    
    with open(TEST_JSON, 'r') as f:
        data = json.load(f)
    
    result = timeline_to_pygenometracks(
        data,
        str(output_ini),
        media_type="video"
    )
    
    assert result is True, "Function should return True on success"
    assert output_ini.exists(), "Output INI file was not created"
    
    png_file = output_ini.with_suffix('.png')
    bed_file = output_ini.with_suffix('.bed')
    
    assert bed_file.exists(), "BED coordinate data file was not created"
    assert png_file.exists(), "PNG visualization file was not created"
    
    config = configparser.ConfigParser()
    config.read(output_ini)
    
    assert 'bed' in config, "Missing bed track in INI file"
    assert 'file' in config['bed'], "Missing file path in bed section"
    assert 'title' in config['bed'], "Missing title in bed section"
    assert str(bed_file) in config['bed']['file'], "Incorrect BED file path in INI"

def test_bed_to_pygenometracks_unit(tmp_path, create_test_files):
    """Unit test for bed_to_pygenometracks function."""
    output_ini = tmp_path / "bed_unit_test.ini"
    
    result = bed_to_pygenometracks(
        bed_file_path=str(TEST_BED_FILE),
        output_path=str(output_ini),
        markers_file_path=str(TEST_MARKERS_FILE)
    )
    
    assert result is True, "Function should return True on success"
    assert output_ini.exists(), "Output INI file was not created"
    
    png_file = output_ini.with_suffix('.png')
    assert png_file.exists(), "PNG visualization file was not created"
    
    config = configparser.ConfigParser()
    config.read(output_ini)
    
    assert 'bed' in config, "Missing bed track in INI file"
    assert 'bed_markers' in config, "Missing markers track in INI file"
    assert 'file' in config['bed'], "Missing file path in bed section"
    assert 'file' in config['bed_markers'], "Missing file path in markers section"
    assert str(TEST_BED_FILE) in config['bed']['file'], "Incorrect BED file path in INI"
    assert str(TEST_MARKERS_FILE) in config['bed_markers']['file'], "Incorrect markers file path in INI"

def test_bed_to_pygenometracks_with_custom_ini_unit(tmp_path, create_test_files):
    """Unit test for bed_to_pygenometracks function with custom INI."""
    output_ini = tmp_path / "custom_ini_unit_test.ini"
    
    result = bed_to_pygenometracks(
        bed_file_path=str(TEST_BED_FILE),
        output_path=str(output_ini),
        markers_file_path=str(TEST_MARKERS_FILE),
        custom_ini_path=str(TEST_INI_FILE)
    )
    
    assert result is True, "Function should return True on success"
    assert output_ini.exists(), "Output INI file was not created"
    
    png_file = output_ini.with_suffix('.png')
    assert png_file.exists(), "PNG visualization file was not created"
    
    config = configparser.ConfigParser()
    config.read(output_ini)
    
    assert 'bed' in config, "Missing bed track in INI file"
    assert 'bed_markers' in config, "Missing markers track in INI file"
    assert 'spacer' in config, "Missing spacer section from custom INI"
    assert 'x-axis' in config, "Missing x-axis section from custom INI"
    assert config['bed']['color'] == '#0000FF', "Custom color not preserved"
    assert config['bed_markers']['color'] == '#FF00FF', "Custom marker color not preserved"
    assert config['bed']['title'] == 'Custom Synteny Track', "Custom title not preserved"
    assert config['bed_markers']['style'] == 'triangles', "Custom marker style not preserved"

@pytest.mark.usefixtures("create_test_files")
def test_timeline_convert_pygenometracks_cli(tmp_path):
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
        assert png_file.exists(), "PNG visualization file was not created"
        
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

@pytest.mark.usefixtures("create_test_files")
def test_timeline_convert_pygenometracks_audio_cli(tmp_path):
    """Test running the 'avtools common timeline' command with pyGenomeTracks output for audio."""
    output_ini = tmp_path / "output_audio.ini"
    command = [
        "avtools", "common", "timeline",
        str(TEST_AUDIO_JSON),
        "--format", "pygenometracks",
        "--type", "audio",
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
        assert png_file.exists(), "PNG visualization file was not created"
        
        with open(output_ini, 'r') as f:
            content = f.read()
            assert '[bed]' in content, "Missing bed track in INI file"
            assert 'file =' in content, "Missing file path in INI file"
            assert 'title =' in content, "Missing title in INI file"
            assert 'Audio' in content, "Missing audio-specific title in INI file"

    except subprocess.CalledProcessError as e:
        print(f"Timeline convert stdout on error:\n{e.stdout}")
        print(f"Timeline convert stderr on error:\n{e.stderr}")
        pytest.fail(f"'timeline' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'timeline' test: {e}")

@pytest.mark.usefixtures("create_test_files")
def test_timeline_convert_bed_input_cli(tmp_path):
    """Test running the 'avtools common timeline' command with BED input."""
    output_ini = tmp_path / "output_bed.ini"
    command = [
        "avtools", "common", "timeline",
        str(TEST_BED_FILE),
        "--format", "pygenometracks",
        "--type", "bed",
        "-o", str(output_ini)
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Timeline convert stdout:\n{result.stdout}")
        print(f"Timeline convert stderr:\n{result.stderr}")

        assert output_ini.exists(), "Output INI file was not created"
        
        png_file = output_ini.with_suffix('.png')
        assert png_file.exists(), "PNG visualization file was not created"
        
        with open(output_ini, 'r') as f:
            content = f.read()
            assert '[bed]' in content, "Missing bed track in INI file"
            assert 'file =' in content, "Missing file path in INI file"
            assert 'title =' in content, "Missing title in INI file"
            assert str(TEST_BED_FILE) in content, "Missing BED file path in INI file"

    except subprocess.CalledProcessError as e:
        print(f"Timeline convert stdout on error:\n{e.stdout}")
        print(f"Timeline convert stderr on error:\n{e.stderr}")
        pytest.fail(f"'timeline' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'timeline' test: {e}")

@pytest.mark.usefixtures("create_test_files")
def test_timeline_convert_bed_with_markers_cli(tmp_path):
    """Test running the 'avtools common timeline' command with BED input and markers."""
    output_ini = tmp_path / "output_bed_markers.ini"
    command = [
        "avtools", "common", "timeline",
        str(TEST_BED_FILE),
        "--format", "pygenometracks",
        "--type", "bed",
        "--markers", str(TEST_MARKERS_FILE),
        "-o", str(output_ini)
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Timeline convert stdout:\n{result.stdout}")
        print(f"Timeline convert stderr:\n{result.stderr}")

        assert output_ini.exists(), "Output INI file was not created"
        
        png_file = output_ini.with_suffix('.png')
        assert png_file.exists(), "PNG visualization file was not created"
        
        with open(output_ini, 'r') as f:
            content = f.read()
            assert '[bed]' in content, "Missing bed track in INI file"
            assert '[bed_markers]' in content, "Missing markers track in INI file"
            assert str(TEST_BED_FILE) in content, "Missing BED file path in INI file"
            assert str(TEST_MARKERS_FILE) in content, "Missing markers file path in INI file"

    except subprocess.CalledProcessError as e:
        print(f"Timeline convert stdout on error:\n{e.stdout}")
        print(f"Timeline convert stderr on error:\n{e.stderr}")
        pytest.fail(f"'timeline' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'timeline' test: {e}")

@pytest.mark.usefixtures("create_test_files")
def test_timeline_convert_bed_with_custom_ini_cli(tmp_path):
    """Test running the 'avtools common timeline' command with BED input and custom INI."""
    output_ini = tmp_path / "output_bed_custom.ini"
    command = [
        "avtools", "common", "timeline",
        str(TEST_BED_FILE),
        "--format", "pygenometracks",
        "--type", "bed",
        "--markers", str(TEST_MARKERS_FILE),
        "--ini", str(TEST_INI_FILE),
        "-o", str(output_ini)
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Timeline convert stdout:\n{result.stdout}")
        print(f"Timeline convert stderr:\n{result.stderr}")

        assert output_ini.exists(), "Output INI file was not created"
        
        png_file = output_ini.with_suffix('.png')
        assert png_file.exists(), "PNG visualization file was not created"
        
        config = configparser.ConfigParser()
        config.read(output_ini)
        
        assert 'bed' in config, "Missing bed track in INI file"
        assert 'bed_markers' in config, "Missing markers track in INI file"
        assert 'spacer' in config, "Missing spacer section from custom INI"
        assert 'x-axis' in config, "Missing x-axis section from custom INI"
        assert config['bed']['color'] == '#0000FF', "Custom color not preserved"
        assert config['bed_markers']['color'] == '#FF00FF', "Custom marker color not preserved"
        assert config['bed']['title'] == 'Custom Synteny Track', "Custom title not preserved"
        assert config['bed_markers']['style'] == 'triangles', "Custom marker style not preserved"

    except subprocess.CalledProcessError as e:
        print(f"Timeline convert stdout on error:\n{e.stdout}")
        print(f"Timeline convert stderr on error:\n{e.stderr}")
        pytest.fail(f"'timeline' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'timeline' test: {e}")
