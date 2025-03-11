#!/bin/bash

# Check if Rosetta 2 is installed
if ! pkgutil --pkg-info com.apple.pkg.RosettaUpdateAuto > /dev/null 2>&1; then
    echo "Installing Rosetta 2..."
    softwareupdate --install-rosetta --agree-to-license
fi

# Check if Intel Homebrew is installed
if ! arch -x86_64 /usr/local/bin/brew --version > /dev/null 2>&1; then
    echo "Installing Intel Homebrew..."
    arch -x86_64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
fi

# Install Intel Python
echo "Installing Intel Python..."
arch -x86_64 /usr/local/bin/brew install python@3.11

# Create Intel Python virtual environment
echo "Creating Intel Python virtual environment..."
arch -x86_64 /usr/local/bin/python3.11 -m venv intel_venv

# Activate virtual environment and install requirements
echo "Installing requirements..."
source intel_venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

# Run build script
echo "Running build script..."
python build.py