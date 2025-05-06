from setuptools import setup, find_packages

setup(
    name="avtools",
    version="0.1.0",
    description="Audio and Video Tools for Media Processing",
    author="Allen Day",
    author_email="allenday@allenday.com",
    url="https://github.com/allenday/avtools",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "avtools=avtools.cli.main:main",
        ],
    },
)
