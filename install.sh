#!/bin/bash
set -e

echo "Making sure submodules are initialized..."
git submodule update --init --recursive

echo "Installing dependencies"
pip install -r requirements.txt0
pip install -r requirements.txt1
pip install -r requirements.txt2
pip install -r requirements.txt3
pip install -r requirements.txt4

echo "Setting up the transnetv2pt module properly..."
cd transnetv2pt
pip install -e .
cd ..

echo "Installation complete!"
