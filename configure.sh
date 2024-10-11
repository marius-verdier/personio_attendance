#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "=== Setting up the project ==="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Error: Python 3 is not installed."
    echo "Please install Python 3 and rerun this script."
    exit 1
fi

# Detect the operating system
OS="$(uname -s)"

# Function to install libgstreamer-plugins-bad1.0-0 on Linux
install_gstreamer_plugin() {
    if [ "$OS" = "Linux" ]; then
        # Check if apt-get is available (Debian/Ubuntu)
        if command -v apt-get &> /dev/null; then
            echo "Detected Linux OS. Attempting to install 'libgstreamer-plugins-bad1.0-0'..."
            sudo apt-get update
            sudo apt-get install -y libgstreamer-plugins-bad1.0-0
        else
            echo "Package manager 'apt-get' not found. Please install 'libgstreamer-plugins-bad1.0-0' manually."
        fi
    fi
}

# Prompt the user for installing the GStreamer plugin
read -p "Do you want to install 'libgstreamer-plugins-bad1.0-0' (may be required on Linux systems)? [y/N]: " install_gst
if [[ "$install_gst" =~ ^[Yy]$ ]]; then
    install_gstreamer_plugin
else
    echo "Skipping installation of 'libgstreamer-plugins-bad1.0-0'."
fi

# Create a virtual environment
echo "Creating a virtual environment in 'venv'..."
python3 -m venv .venv

# Activate the virtual environment
echo "Activating the virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

# Upgrade pip to the latest version
echo "Upgrading pip..."
pip install --upgrade pip

# Install the required Python packages
echo "Installing Python packages from requirements.txt..."
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install

echo "=== Setup completed successfully! ==="

echo ""
echo "To activate the virtual environment in the future, run:"
echo "source .venv/bin/activate"
echo ""
echo "You can now run your project."