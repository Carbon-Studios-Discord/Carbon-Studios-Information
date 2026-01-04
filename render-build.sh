#!/usr/bin/env bash
set -o errexit

# 1. Install Chrome and the Virtual Screen software (Xvfb)
STORAGE_DIR=/opt/render/project/.render
if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Downloading Chrome"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x ./google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome
  rm ./google-chrome-stable_current_amd64.deb
else
  echo "...Using Chrome from cache"
fi

# 2. Install necessary system libraries for the virtual screen
# This ensures pyvirtualdisplay works
apt-get update && apt-get install -y xvfb

# 3. Install Python dependencies
pip install -r requirements.txt
