#!/usr/bin/env bash
set -euo pipefail
sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc
sudo apt-get update
sudo apt-get install -y bc bison build-essential ccache curl flex g++-multilib gcc-multilib git gnupg gperf lib32ncurses-dev lib32z1-dev libelf-dev liblz4-tool libncurses-dev libsdl1.2-dev libssl-dev libxml2 libxml2-utils lzop openjdk-11-jdk python3 rsync unzip zip zlib1g-dev
mkdir -p "$HOME/bin"
curl -fL https://storage.googleapis.com/git-repo-downloads/repo -o "$HOME/bin/repo"
chmod +x "$HOME/bin/repo"
echo "$HOME/bin" >> "$GITHUB_PATH"
git config --global user.name recovery-builder
git config --global user.email recovery-builder@users.noreply.github.com
coral_swap_file="$RUNNER_TEMP/orangefox-swap"
sudo fallocate -l 8G "$coral_swap_file"
sudo chmod 600 "$coral_swap_file"
sudo mkswap "$coral_swap_file"
sudo swapon "$coral_swap_file"
free -h
df -h
