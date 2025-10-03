#!/bin/sh
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get purge --autoremove geany thonny chromium vlc -y
sudo apt-get install pipenv # FIXME: Use pip --break-system-packages instead for latest?
sudo rm /etc/sudoers.d/010_pi-nopasswd  # Require password for sudo.
