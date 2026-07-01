#!/bin/bash
# Spoolman Installation Script for Klipper SBCs (CB1 / Raspberry Pi / Orange Pi, etc.)
#
# Run this as your normal printer user (NOT with sudo) — it calls sudo itself
# where root is required. Paths and the systemd service user are derived from
# whoever runs it.
#
# Spoolman requires Python 3.9+. On older OS images (e.g. Debian Buster, which
# ships Python 3.7) this script fetches a prebuilt, isolated Python via uv and
# uses it ONLY for Spoolman's virtualenv — the system Python is left untouched
# so Klipper and Moonraker keep running on it. No compiling from source.

set -eo pipefail

if [ -z "${HOME}" ]; then
    echo "\$HOME is not set; cannot determine install location. Aborting." >&2
    exit 1
fi

SPOOLMAN_USER="$(whoami)"
SPOOLMAN_DIR="${HOME}/spoolman"
SPOOLMAN_VERSION="0.19.3"
DOWNLOAD_URL="https://github.com/Donkie/Spoolman/releases/download/v${SPOOLMAN_VERSION}/spoolman.zip"

# Python to fetch via uv when the system Python is too old (< 3.9).
PYTHON_VERSION="3.11"

if [ "$(id -u)" -eq 0 ]; then
    echo "Please run this script as your normal user, not as root/sudo." >&2
    echo "It will prompt for sudo only when needed." >&2
    exit 1
fi

echo "=== Installing Spoolman v${SPOOLMAN_VERSION} ==="
echo "User:      ${SPOOLMAN_USER}"
echo "Directory: ${SPOOLMAN_DIR}"

# Install base dependencies (unzip is required to extract the release archive).
# python3-venv may be unavailable on EOL distros (e.g. Debian Buster) — that's
# OK because the uv fallback below handles old Python without needing it.
echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip unzip curl || true
sudo apt-get install -y python3-venv 2>/dev/null || true

# Create directory
echo "Creating Spoolman directory..."
rm -rf "${SPOOLMAN_DIR}"
mkdir -p "${SPOOLMAN_DIR}"
cd "${SPOOLMAN_DIR}"

# Download latest release. The Spoolman release ships a .zip (not .tar.gz).
# -f makes curl exit non-zero on HTTP errors (e.g. 404) instead of silently
# writing the error page to the output file.
echo "Downloading Spoolman..."
curl -fSL "${DOWNLOAD_URL}" -o spoolman.zip
unzip -q spoolman.zip
rm spoolman.zip

# --- Set up the Python environment -----------------------------------------
# Use the system python3 if it is new enough (>= 3.9). Otherwise fetch a
# prebuilt, isolated CPython via uv (a small download, no compiling) and build
# the venv from it. The system Python is never replaced.
echo "Checking Python version..."
if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    echo "System python3 ($(python3 -V 2>&1)) is new enough."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -e .
else
    echo "System python3 ($(python3 -V 2>&1 || echo 'unknown')) is older than 3.9 — Spoolman needs 3.9+."
    echo "Fetching a prebuilt Python ${PYTHON_VERSION} via uv (no compiling)..."

    # Install uv (a single static binary) if not already present. Download the
    # installer to a temp file and run it explicitly rather than piping
    # `curl | sh`, so it can be inspected and a truncated download can't run.
    if ! command -v uv >/dev/null 2>&1; then
        UV_INSTALLER="$(mktemp)"
        curl -fsSL https://astral.sh/uv/install.sh -o "$UV_INSTALLER"
        sh "$UV_INSTALLER"
        rm -f "$UV_INSTALLER"
    fi
    # uv installs to ~/.local/bin (newer installers) or ~/.cargo/bin (older)
    export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
    hash -r 2>/dev/null || true

    if ! command -v uv >/dev/null 2>&1; then
        echo "uv installation failed or is not on PATH." >&2
        echo "Open a new shell and re-run, or install uv manually: https://docs.astral.sh/uv/" >&2
        exit 1
    fi

    # Download a standalone CPython and build the venv from it
    uv python install "${PYTHON_VERSION}"
    uv venv --python "${PYTHON_VERSION}" .venv
    source .venv/bin/activate
    uv pip install -e .
fi

# Create .env file
echo "Creating configuration..."
cat > .env << 'EOF'
# Spoolman Configuration
SPOOLMAN_DB_TYPE=sqlite
SPOOLMAN_HOST=0.0.0.0
SPOOLMAN_PORT=7912
SPOOLMAN_LOGGING_LEVEL=info
EOF

# Create systemd service. The service runs uvicorn from the venv, so it uses
# whichever Python the venv was built with (system or uv-provided).
echo "Creating systemd service..."
sudo tee /etc/systemd/system/spoolman.service > /dev/null << EOF
[Unit]
Description=Spoolman - Filament Spool Manager
After=network.target

[Service]
Type=simple
User=${SPOOLMAN_USER}
WorkingDirectory=${SPOOLMAN_DIR}
ExecStart=${SPOOLMAN_DIR}/.venv/bin/uvicorn spoolman.main:app --host 0.0.0.0 --port 7912
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "Starting Spoolman service..."
sudo systemctl daemon-reload
sudo systemctl enable spoolman
sudo systemctl start spoolman

# Wait and check status
sleep 3
sudo systemctl status spoolman --no-pager

echo ""
echo "=== Spoolman Installation Complete ==="
echo "Web UI: http://$(hostname -I | awk '{print $1}'):7912"
echo ""
echo "Next steps:"
echo "1. Add to Moonraker config:"
echo "   [spoolman]"
echo "   server: http://localhost:7912"
echo ""
echo "2. Enable in Klipper MCP:"
echo "   Set SPOOLMAN_ENABLED=true"
