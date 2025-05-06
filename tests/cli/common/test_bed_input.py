import os
from pathlib import Path

import pytest
import subprocess

TEST_DATA_DIR = Path(__file__).parent.parent.parent / "data"
TEST_BED_FILE = TEST_DATA_DIR / "test_synteny.bed"
TEST_MARKERS_FILE = TEST_DATA_DIR / "test_markers.bed"
TEST_INI_FILE = TEST_DATA_DIR / "test_config.ini"

@pytest.fixture(scope="module")
def create_test_bed_files():
    """Create test BED files for synteny visualization."""
    if not TEST_DATA_DIR.exists():
        TEST_DATA_DIR.mkdir(parents=True)
    
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
    
    return TEST_BED_FILE, TEST_MARKERS_FILE, TEST_INI_FILE

@pytest.mark.usefixtures("create_test_bed_files")
def test_bed_input_basic(tmp_path):
    """Test running the 'avtools common timeline' command with BED input."""
    output_ini = tmp_path / "output.ini"
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
        assert png_file.exists(), "Output PNG file was not created"
        
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

@pytest.mark.usefixtures("create_test_bed_files")
def test_bed_input_with_markers(tmp_path):
    """Test running the 'avtools common timeline' command with BED input and markers."""
    output_ini = tmp_path / "output_markers.ini"
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
        assert png_file.exists(), "Output PNG file was not created"
        
        with open(output_ini, 'r') as f:
            content = f.read()
            assert '[bed]' in content, "Missing bed track in INI file"
            assert '[bed_markers]' in content, "Missing markers track in INI file"
            assert str(TEST_MARKERS_FILE) in content, "Markers file path not found in INI file"

    except subprocess.CalledProcessError as e:
        print(f"Timeline convert stdout on error:\n{e.stdout}")
        print(f"Timeline convert stderr on error:\n{e.stderr}")
        pytest.fail(f"'timeline' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'timeline' test: {e}")

@pytest.mark.usefixtures("create_test_bed_files")
def test_bed_input_with_custom_ini(tmp_path):
    """Test running the 'avtools common timeline' command with BED input and custom INI."""
    output_ini = tmp_path / "output_custom.ini"
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
        assert png_file.exists(), "Output PNG file was not created"
        
        with open(output_ini, 'r') as f:
            content = f.read()
            assert 'Custom Synteny Track' in content, "Custom title not found in INI file"
            assert 'Custom Markers' in content, "Custom markers title not found in INI file"
            assert '#0000FF' in content, "Custom color not found in INI file"
            assert '#FF00FF' in content, "Custom marker color not found in INI file"

    except subprocess.CalledProcessError as e:
        print(f"Timeline convert stdout on error:\n{e.stdout}")
        print(f"Timeline convert stderr on error:\n{e.stderr}")
        pytest.fail(f"'timeline' command failed with exit code {e.returncode}: {command}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during 'timeline' test: {e}")
