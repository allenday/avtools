#!/bin/bash
set -e

echo "Making sure submodules are initialized..."
git submodule update --init --recursive

echo "Setting up the wd14-tagger-standalone module properly..."
cd wd14-tagger-standalone
pip install -e .
cd ..

echo "Setting up the transnetv2pt module properly..."
cd transnetv2pt
pip install -e .
cd ..

echo "Installing dependencies"
#TODO wd14 seems to require numpy 2.2.2. maybe not?
#pip uninstall numpy
pip install -r requirements.txt0

echo "Setting up the NATTEN module properly..."
cd NATTEN
make install
cd ..

pip install -r requirements.txt1 --no-build-isolation "torch==2.6.0"

pip install -e .

echo "Installation complete!"
