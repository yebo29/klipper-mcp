#!/bin/bash
# Klipper MCP Server Installation Script
# Run this from inside the cloned repository:  bash install.sh
# Compatible with Python 3.9+
#
# The service runs FROM the cloned repo directory, so `git pull` updates the
# running server — nothing is copied to a second location. Paths and the
# systemd user/group are derived from where this script lives and who runs it.

set -e

# Run as the normal printer user, not root. The service should run unprivileged;
# this script calls sudo itself only where root is actually required (systemd,
# log/unit files). Running the whole thing as root would install the unit as
# User=root and leave the repo venv/files root-owned.
if [ "$(id -u)" -eq 0 ]; then
    echo "Please run this script as your normal user, not as root/sudo." >&2
    echo "It will prompt for sudo only when needed." >&2
    exit 1
fi

echo "=========================================="
echo "Klipper MCP Server Installer"
echo "=========================================="

# Check Python version (server + dependencies require Python 3.9+)
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 not found. Install Python 3.9+ and re-run." >&2
    exit 1
fi
# Use %-formatting (not an f-string) so this prints cleanly even on Python < 3.6,
# letting the version check below emit a friendly message instead of a SyntaxError.
PYTHON_VERSION=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "Python version: $PYTHON_VERSION"
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    echo "Error: Python 3.9+ is required (found $PYTHON_VERSION)." >&2
    echo "       aiohttp>=3.13 and python-dotenv>=1.1.1 do not support older versions." >&2
    exit 1
fi
# The venv module is needed to create the virtualenv below; on Debian/Ubuntu it
# ships separately (python3-venv) and may be missing even when python3 is new.
if ! python3 -c 'import venv' >/dev/null 2>&1; then
    echo "Error: the Python 'venv' module is not available." >&2
    echo "       Install it (e.g. 'sudo apt-get install python3-venv') and re-run." >&2
    exit 1
fi

# Resolve the repo directory (where this script lives) and the running user.
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_NAME="klipper-mcp"
CURRENT_USER="$(whoami)"
INSTALL_GROUP="$(id -gn)"
USER_HOME="$(getent passwd "$CURRENT_USER" | cut -d: -f6)"
PRINTER_DATA_DIR="${PRINTER_DATA_DIR:-$USER_HOME/printer_data}"

echo "Installing as user: $CURRENT_USER ($INSTALL_GROUP)"
echo "Install directory (service runs from clone): $INSTALL_DIR"

# Runtime directories (gitignored) created in place inside the repo
echo "Creating runtime directories..."
mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/backups"

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"

# Activate venv and install dependencies
echo "Installing dependencies..."
# shellcheck source=/dev/null  # activate is generated at install time
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$INSTALL_DIR/requirements.txt"

# Create config from template if needed
if [ ! -f "$INSTALL_DIR/config.py" ]; then
    echo "Creating default config.py..."
    # config.py lives in the repo working tree (gitignored); create it from the
    # tracked example on first install. Existing config.py is left untouched.
    cp "$INSTALL_DIR/config.example.py" "$INSTALL_DIR/config.py"
fi

# Generate the systemd unit pointing at THIS directory (the clone) and user.
# Written straight to /etc so the tracked klipper-mcp.service template in the
# repo is left untouched. Logging goes to journald (view with journalctl).
echo "Generating systemd service file..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null << SVCEOF
[Unit]
Description=Klipper MCP Server
After=network.target moonraker.service
Wants=moonraker.service

[Service]
Type=simple
User=$CURRENT_USER
Group=$INSTALL_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$VENV_DIR/bin/python server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

# Install systemd service
echo "Installing systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# Add service to moonraker.asvc (allowed services list) so Moonraker can
# start/stop/restart klipper-mcp. Only if the printer_data dir exists; don't
# abort the whole install if it's missing or in a non-standard location.
if [ -d "$PRINTER_DATA_DIR" ]; then
    ASVC_FILE="$PRINTER_DATA_DIR/moonraker.asvc"
    if ! grep -qxF 'klipper-mcp' "$ASVC_FILE" 2>/dev/null; then
        echo 'klipper-mcp' >> "$ASVC_FILE"
        echo "Registered klipper-mcp in $ASVC_FILE"
    fi
else
    echo "Note: $PRINTER_DATA_DIR not found — skipping moonraker.asvc registration."
    echo "      Set PRINTER_DATA_DIR and re-run, or add 'klipper-mcp' to moonraker.asvc manually."
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit the configuration file:"
echo "   nano $INSTALL_DIR/config.py"
echo ""
echo "2. Set ARMED=True when ready to enable dangerous commands"
echo ""
echo "3. Start the service:"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo "4. Check service status:"
echo "   sudo systemctl status $SERVICE_NAME"
echo ""
echo "5. View logs:"
echo "   journalctl -u $SERVICE_NAME -f"
echo ""
echo "MCP server will be available at:"
echo "   http://$(hostname -I | awk '{print $1}'):${MCP_PORT:-8000}/mcp"
echo ""
