#!/usr/bin/env bash
set -o errexit

# --- 1. DOWNLOAD CHROME ---
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

# --- 2. GO BACK TO PROJECT ROOT ---
# This is the important part! We need to go back to where requirements.txt is.
cd $HOME/project/src || cd /opt/render/project/src

# --- 3. INSTALL REQUIREMENTS ---
# Use 'pip install' on the file in the current directory
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "ERROR: requirements.txt not found in $(pwd)"
    ls -R # This will print all files to your log so you can see where it is
    exit 1
fi
