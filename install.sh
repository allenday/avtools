#!/bin/bash
set -e

echo "Making sure submodules are initialized..."
git submodule update --init --recursive

echo "Installing build dependencies..."
pip install --upgrade pip setuptools wheel
pip install build

echo "Installing PyTorch (needed for NATTEN build)..."
pip install torch==2.6.0

echo "Setting up the wd14-tagger-standalone module properly..."
cd wd14-tagger-standalone
pip install -e .
cd ..

echo "Setting up the transnetv2pt module properly..."
cd transnetv2pt
pip install -e .
cd ..

echo "Installing NATTEN with specific commit hash..."
pip install git+https://github.com/SHI-Labs/NATTEN.git@3b54c76185904f3cb59a49fff7bc044e4513d106#egg=natten --no-build-isolation

echo "Installing Cython and madmom dependencies..."
pip install Cython>=0.29.24

echo "Installing madmom and allin1..."
pip install git+https://github.com/CPJKU/madmom.git@0551aa8f48d71a367d92b5d3a347a0cf7cd97cc9#egg=madmom --no-build-isolation
pip install allin1==1.1.0

echo "Installing the package with all dependencies..."
pip install -e .

echo "Installation complete!"
