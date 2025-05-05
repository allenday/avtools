#!/bin/bash
set -e

echo "Making sure submodules are initialized..."
git submodule update --init --recursive

echo "Installing build dependencies..."
pip install --upgrade pip setuptools wheel
pip install build

echo "Setting up the wd14-tagger-standalone module properly..."
cd wd14-tagger-standalone
pip install -e .
cd ..

echo "Setting up the transnetv2pt module properly..."
cd transnetv2pt
pip install -e .
cd ..

echo "Installing PyTorch (needed for NATTEN build)..."
pip install torch==2.6.0

echo "Setting up the NATTEN module properly..."
cd NATTEN
make install
cd ..

echo "Installing the package with all dependencies..."
pip install -e .

echo "Installation complete!"
