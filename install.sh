#!/bin/bash
set -e

echo "Making sure submodules are initialized..."
git submodule update --init --recursive

echo "Installing dependencies with --no-build-isolation flag..."
pip install -r requirements.txt --no-build-isolation

echo "Setting up the transnetv2pt module properly..."
cd transnetv2pt
pip install -e .
cd ..

echo "Installation complete!" 