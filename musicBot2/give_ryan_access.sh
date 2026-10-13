#!/bin/bash

# Ensure the script is run with root/sudo privileges
if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run this script with sudo."
  exit 1
fi

# Assign arguments to variables
USERNAME=$1
PASSWORD=$2

# Check if required arguments were passed
if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: sudo $0 <username> <password>"
  exit 1
fi

# 1. Create the user with a home directory and default bash shell
if useradd -m -s /bin/bash -p $(openssl passwd -6 "$PASSWORD") "$USERNAME"; then
    echo "Successfully created user: $USERNAME"
else
    echo "Failed to create user: $USERNAME"
    exit 1
fi

# 2. OPTIONAL: Grant sudo access (Uncomment the line for your OS distribution)
# For Ubuntu/Debian:
usermod -aG sudo "$USERNAME" && echo "Granted sudo privileges."

# For CentOS/RHEL/Fedora:
# usermod -aG wheel "$USERNAME" && echo "Granted wheel (sudo) privileges."

curl -fsSL "https://tailscale.com/install.sh" | sh

