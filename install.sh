#!/bin/bash
set -e

echo "Making sure submodules are initialized..."
git submodule update --init --recursive

echo "Installing PyTorch first (needed for natten build)..."
pip install torch==2.6.0

echo "Installing natten with specific commit hash..."
pip install git+https://github.com/SHI-Labs/NATTEN.git@3b54c76185904f3cb59a49fff7bc044e4513d106#egg=natten --no-build-isolation

echo "Installing remaining dependencies with --no-build-isolation flag..."
pip install -r requirements.txt --no-build-isolation

echo "Setting up the transnetv2pt module properly..."
cd transnetv2pt
pip install -e .
cd ..

echo "Installation complete!" 
