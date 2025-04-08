from setuptools import setup, find_packages
import os
import subprocess

def install_requirements():
    """Install requirements with --no-build-isolation flag."""
    subprocess.check_call([
        'pip', 'install', '-r', 'requirements.txt', '--no-build-isolation'
    ])

class CustomInstallCommand:
    def run(self):
        install_requirements()

setup(
    name="avtools",
    version="0.1.0",
    packages=find_packages(),
    cmdclass={
        'install': CustomInstallCommand,
    },
)

if __name__ == "__main__":
    # If this script is run directly, install the requirements
    install_requirements() 