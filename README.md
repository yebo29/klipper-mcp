# Klipper MCP Server

A Model Context Protocol (MCP) server for controlling Klipper 3D printers via the Moonraker API. Lets AI assistants like Claude observe and control your printer (Voron, RatRig, or any Klipper machine) from VS Code, Claude Desktop, or Claude Code.

Exposes **100+ tools** — from basic control to diagnostics and toolchanger management.

Fork of [Charleslotto/klipper-mcp](https://github.com/Charleslotto/klipper-mcp) adding: read-only mode for AI agents, `.env`/journald config, removed hard-coded user, secure key/PIN generation, NGINX SSL setup, Claude Desktop/VS Code/Claude Code client docs, and Moonraker `update_manager` auto-updates.

## Tools

> 🔒 = **write tool** — changes printer or system state. Write tools are never registered when `READ_ONLY=true` (see [Security](#security)); many also require `ARMED=true` and/or the admin PIN.

<details>
<summary><b>Full tool catalog (click to expand)</b></summary>

### 🖨️ Core Printer Control

| Tool | Description |
| ------ | ------------- |
| `get_printer_status` | Full status: temps, position, state |
| `get_temperatures` | Current temperatures for all heaters |
| `get_server_info` | Moonraker server info and version |
| `set_temperature` 🔒 | Set a heater (hotend/bed) target temp |
| `run_gcode` 🔒 | Execute any G-code command |
| `home_printer` 🔒 | Home X/Y/Z or all axes |
| `start_print` 🔒 | Start a print job |
| `pause_print` / `resume_print` 🔒 | Print flow control |
| `cancel_print` 🔒 | Cancel current print |
| `restart_klipper` 🔒 | Firmware restart |
| `emergency_stop` 🔒 | Immediate halt (requires admin PIN) |

### 🔧 StealthChanger / Toolchanger

| Tool | Description |
| ------ | ------------- |
| `get_active_tool` | Current tool status |
| `get_tool_offsets` | Tool offset values |
| `get_dock_positions` | Configured dock positions |
| `select_tool` 🔒 | Activate a tool (T0–TN) |
| `pickup_tool` / `dropoff_tool` 🔒 | Pick up / return tool to dock |
| `initialize_toolchanger` 🔒 | Run init sequence |
| `tool_align_start` / `tool_align_test` / `tool_align_done` 🔒 | Alignment workflow |
| `start_crash_detection` / `stop_crash_detection` 🔒 | Crash detection control |
| `set_tool_temperature` 🔒 | Set a tool's extruder temp |
| `quad_gantry_level` 🔒 | Run QGL procedure |

### ⚡ TMC Stepper Driver Control

| Tool | Description |
| ------ | ------------- |
| `get_tmc_status` | Driver status, currents, temps |
| `dump_tmc_registers` | Register diagnostics |
| `get_tmc_field` | Read a register field |
| `get_autotune_status` | TMC Autotune configuration |
| `list_tmc_steppers` | All TMC-equipped steppers |
| `set_tmc_current` 🔒 | Adjust run/hold current |
| `set_tmc_field` 🔒 | Write a register field |

### 💡 LED Effects (klipper-led_effect)

| Tool | Description |
| ------ | ------------- |
| `list_led_effects` | Common effect names |
| `list_led_scenes` | Preset scenes |
| `set_led_effect` 🔒 | Activate an effect |
| `stop_led_effect` / `stop_all_led_effects` 🔒 | Stop effects |
| `set_led_direct` 🔒 | Direct RGB/RGBW control |
| `set_led_scene` 🔒 | Apply a scene preset |

### 📁 File Operations

| Tool | Description |
| ------ | ------------- |
| `list_files` | List any printer directory |
| `list_gcode_files` | Browse G-code files |
| `list_config_files` | Klipper config files |
| `read_file` | Read file contents (config/logs/etc.) |
| `get_gcode_metadata` | Slicer settings, thumbnails |
| `search_in_file` | Search file contents |
| `write_file` 🔒 | Write a file (requires admin PIN) |
| `delete_file` 🔒 | Delete a file (requires admin PIN) |

### 📷 Camera & Timelapse

| Tool | Description |
| ------ | ------------- |
| `capture_snapshot` | Capture current frame (base64) |
| `get_camera_stream_url` | MJPEG stream URL |
| `get_timelapse_settings` | Current timelapse config |
| `list_timelapses` | Rendered timelapse videos |
| `set_timelapse_enabled` 🔒 | Enable/disable timelapse |
| `configure_timelapse` 🔒 | Adjust settings |
| `take_timelapse_frame` 🔒 | Manual frame capture |
| `render_timelapse` 🔒 | Trigger video render |

### 📊 Print Statistics

| Tool | Description |
| ------ | ------------- |
| `get_print_history` | Past prints with filtering |
| `get_print_totals` | Cumulative statistics |
| `get_job_details` | Details of a single job |
| `get_filament_usage_summary` | Filament usage summary |
| `get_recent_prints` | Prints in the last N hours |
| `get_average_print_stats` | Average metrics |

### 🔍 Diagnostics & Troubleshooting

| Tool | Description |
| ------ | ------------- |
| `parse_klippy_log` | Analyze log for issues |
| `get_recent_errors` | Recent errors with context |
| `get_log_summary` | Log activity overview |
| `get_log_files` | List log files with sizes |
| `check_common_issues` | Config/state problem detection |
| `get_mcu_status` | MCU info and timing |
| `get_gcode_history` | Recent G-code responses |
| `diagnose_problem` | Symptom-based troubleshooting |
| `clear_old_logs` 🔒 | Delete old log files |
| `truncate_log` 🔒 | Truncate a log file |

### 🌡️ Temperature & Bed Mesh

| Tool | Description |
| ------ | ------------- |
| `get_temperature_history` | Historical temp data |
| `detect_temperature_anomalies` | Anomaly detection |
| `get_bed_mesh` | Current mesh and statistics |
| `get_bed_mesh_profiles` | List saved meshes |
| `get_heater_pid_params` | PID parameters for a heater |
| `load_bed_mesh_profile` 🔒 | Load a mesh profile |
| `calibrate_bed_mesh` 🔒 | Run bed mesh calibration |
| `save_bed_mesh_profile` 🔒 | Save current mesh |
| `clear_bed_mesh` 🔒 | Clear active mesh |

### 🧵 Spoolman Integration

| Tool | Description |
| ------ | ------------- |
| `list_spools` | All tracked spools |
| `get_spool_details` | Full spool info |
| `get_active_spool` | Currently loaded spool |
| `get_filament_vendors` | Filament vendors |
| `get_low_filament_spools` | Low filament warnings |
| `get_filament_usage_by_material` | Material usage statistics |
| `set_active_spool` 🔒 | Set the active spool |
| `clear_active_spool` 🔒 | Clear the active spool |

### 🔔 Notifications

| Tool | Description |
| ------ | ------------- |
| `get_notification_config` | Current notification config |
| `send_notification` 🔒 | Multi-channel notify (Discord/Slack/Pushover/Moonraker) |
| `announce_tts` 🔒 | Text-to-speech announcement |
| `notify_print_complete` 🔒 | Print completion alert |
| `notify_temperature_alert` 🔒 | Temperature alert |
| `console_message` 🔒 | Post to Mainsail/Fluidd console |
| `test_notifications` 🔒 | Test all channels |

### 💾 Backup & Maintenance

| Tool | Description |
| ------ | ------------- |
| `backup_config` | Backup all configs |
| `list_backups` | Available backups |
| `check_maintenance_due` | Maintenance alerts |
| `get_maintenance_history` | Maintenance log |
| `get_audit_log` | Security audit trail |
| `export_printer_data` | Full data export to JSON |
| `restore_config` 🔒 | Restore from backup (requires admin PIN) |
| `log_maintenance` 🔒 | Record a maintenance action |

### 📝 G-code Analysis

| Tool | Description |
| ------ | ------------- |
| `analyze_gcode_file` | Full file analysis |
| `validate_gcode` | Check for common issues |
| `extract_gcode_comments` | Slicer comments |
| `get_gcode_move_stats` | Movement statistics |
| `get_layer_gcode` | Extract a specific layer |
| `find_gcode_section` | Find text within a file |

### 🖥️ System Management

| Tool | Description |
| ------ | ------------- |
| `get_system_info` | CPU, memory, disk, temp |
| `get_network_info` | IP addresses, WiFi |
| `check_updates` | Available updates |
| `get_service_status` | Service states |
| `get_moonraker_config` | Moonraker info |
| `get_printer_objects` | Available Klipper objects |
| `update_component` 🔒 | Update Klipper/Moonraker/etc. |
| `refresh_update_status` 🔒 | Refresh update status from repos |
| `restart_service` 🔒 | Restart a service |
| `reboot_system` 🔒 | System reboot (requires ARMED) |
| `shutdown_system` 🔒 | System shutdown (requires ARMED) |

</details>

## Installation

### Prerequisites

- Klipper + Moonraker running on the printer
- Python 3.9+ on the CB1/Raspberry Pi
- Network access between client and printer
- An MCP client: VS Code (Copilot), Claude Desktop, or Claude Code
- An HTTPS reverse proxy (recommended — see below)

### Quick Start

```bash
# 1. SSH into the printer, then clone
ssh <user>@192.168.x.x
cd ~ && git clone https://github.com/yebo29/klipper-mcp.git && cd klipper-mcp

# 2. Create configs from templates
cp config.example.py config.py
cp .env.example .env

# 3. Generate a secure API key and a 6-digit admin PIN
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
python3 -c "import secrets; print(secrets.randbelow(900000) + 100000)"

# 4. Paste both into .env, set MOONRAKER_URL, etc.
nano .env

# 5. Install and start (install.sh is already executable)
./install.sh
sudo systemctl enable --now klipper-mcp
sudo systemctl status klipper-mcp
```

**Why two secrets?** `API_KEY` authenticates every request. `ADMIN_PIN` is an *extra* gate on destructive ops (file delete, config restore, reboot). Treat both like passwords; the `secrets` one-liners produce cryptographically random values.

### Auto-updates via Moonraker

Add to Moonraker's `update_manager`:

```ini
[update_manager klipper-mcp]
type: git_repo
path: ~/klipper-mcp
origin: https://github.com/yebo29/klipper-mcp.git
primary_branch: main
managed_services: klipper-mcp
requirements: requirements.txt
env: ~/klipper-mcp/venv/bin/python
install_script: install.sh
```

Then add `klipper-mcp` as a line in `~/printer_data/moonraker.asvc` (so Moonraker may restart the service) and `sudo systemctl restart moonraker`.

### Verify

```bash
sudo systemctl status klipper-mcp
curl -H "X-API-Key: your-api-key" http://<printer_hostname>:8000/health
journalctl -u klipper-mcp -f
```

## Configuration

Settings come from `.env` (loaded automatically by `config.py` via `python-dotenv`), the real environment, or `config.py` defaults — in that precedence order. `.env` is gitignored, so it's the easiest place to keep secrets.

Full reference (`config.py`):

```python
# Moonraker connection
MOONRAKER_URL = "http://localhost:7125"
PRINTER_NAME  = "Voron"

# MCP server
MCP_HOST = "0.0.0.0"
MCP_PORT = 8000
MCP_TRANSPORT = "http"          # or "stdio" for local use

# Security
API_KEY   = "your-secret-key"   # required for all API calls
ARMED     = False               # True to enable dangerous ops
READ_ONLY = False               # True to unregister ALL write tools
ADMIN_PIN = "123456"            # required for destructive ops

# Camera
CAMERA_SNAPSHOT_URL = "http://localhost/webcam/?action=snapshot"
CAMERA_STREAM_URL   = "http://localhost/webcam/?action=stream"

# Spoolman (optional)
SPOOLMAN_ENABLED = True
SPOOLMAN_URL     = "http://localhost:7912"

# Notifications (optional)
DISCORD_WEBHOOK_URL = ""
SLACK_WEBHOOK_URL   = ""
PUSHOVER_USER_KEY   = ""
PUSHOVER_API_TOKEN  = ""

# Text-to-Speech (optional)
TTS_ENABLED = False
TTS_RATE    = 150
TTS_VOLUME  = 1.0

# Maintenance intervals (print hours)
MAINTENANCE_INTERVALS = {"nozzle": 200, "belts": 500, "linear_rails": 1000, "filters": 100}

# StealthChanger / Toolchanger
TOOL_COUNT = 4                  # number of tools (T0-T3)
```

**Upgrading?** `install.sh` only creates `config.py` when missing, so an old `config.py` won't have the `load_dotenv` block and will ignore `.env`. Copy the block from `config.example.py`, or re-create it with `cp config.example.py config.py` (back up settings first).

### Persistent env vars (systemd override)

Shell `export` / `~/.bashrc` don't reach the service — it runs under systemd, not your login shell. To set variables that survive logoff and reboot, use a drop-in override:

```bash
sudo systemctl edit klipper-mcp
# In the editor:
[Service]
Environment="SPOOLMAN_ENABLED=true"
Environment="SPOOLMAN_URL=https://spoolman.example.com"

sudo systemctl daemon-reload && sudo systemctl restart klipper-mcp
sudo systemctl show klipper-mcp -p Environment   # confirm
```

This writes to `/etc/systemd/system/klipper-mcp.service.d/override.conf`, leaving the shipped unit untouched so updates won't clobber it. One `Environment=` line per variable.

## Reverse Proxy + HTTPS (Recommended)

Direct `http://<pi>:8000` works for a quick test, but a HTTPS reverse proxy is worth it:

1. **TLS termination** — Claude Desktop's connector flow *requires* HTTPS; other clients send `X-API-Key` in cleartext over plain HTTP.
2. **Server-side auth** — the proxy injects `X-API-Key`, so the secret lives on your server and clients just point at the HTTPS URL.

Shape: `Client → HTTPS → nginx (injects X-API-Key) → http://localhost:8000 → klipper-mcp`

**Prerequisites:** a domain with a DNS record for the printer (Tailscale, Cloudflare Tunnel, or split-horizon LAN DNS all work) and a TLS cert (Let's Encrypt via DNS-01 is most portable).

### Option A: Raw nginx

Save as `/etc/nginx/sites-available/klipper-mcp.conf` (adjust paths/domain):

```nginx
server {
    listen 443 ssl http2;
    server_name printer.example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # Inject the API key server-side. Clients never need it.
        proxy_set_header X-API-Key "<paste-your-API_KEY-here>";

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # MCP streams JSON-RPC. Disable buffering so events flow promptly.
        proxy_buffering           off;
        proxy_cache               off;
        proxy_read_timeout        3600s;
        proxy_send_timeout        3600s;
        chunked_transfer_encoding off;

        client_max_body_size 100m;   # raise for large G-code uploads
    }
}

# Optional: redirect http -> https
server {
    listen 80;
    server_name printer.example.com;
    return 301 https://$host$request_uri;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/klipper-mcp.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Option B: NGINX Proxy Manager (UI)

**Proxy Hosts → Add Proxy Host:**

- **Domain**: `printer.example.com` · **Scheme**: `http` · **Forward**: Pi IP, port `8000`
- **Cache Assets**: OFF · **Block Common Exploits**: OFF (interferes with JSON-RPC) · **Websockets**: ON
- **SSL tab**: pick/request a cert · **Force SSL**: ON · **HTTP/2**: ON

**Advanced tab** — paste:

```nginx
proxy_set_header X-API-Key "<paste-your-API_KEY-here>";

proxy_buffering           off;
proxy_cache               off;
proxy_read_timeout        3600s;
proxy_send_timeout        3600s;
chunked_transfer_encoding off;
client_max_body_size      100m;
```

### Verify the proxy

From a client, *after* installing the MCP server:

```bash
curl -sv https://printer.example.com/health 2>&1 | grep -E "HTTP|< [A-Za-z]"
```

Expect `HTTP/2 200` (no `X-API-Key` — nginx injected it).

- `502` → nginx can't reach klipper-mcp; check forward host/port.
- `401` → header injection failed; check the `proxy_set_header` line for typos/quotes/semicolon.
- `Connection refused` → klipper-mcp bound to `127.0.0.1`; set `MCP_HOST = "0.0.0.0"` or run nginx on the same host.

**Trust boundary:** injecting the key at the proxy shifts auth from "anyone with the key" to "anyone who can reach the vhost" — an improvement on a LAN. If the hostname is publicly resolvable, layer on an `allow`/`deny` block, Cloudflare Access, Tailscale, or Basic auth. Decide before it goes live.

## MCP Clients

Examples use `https://printer.example.com/mcp` (your reverse proxy). Connecting directly? Swap in `http://<pi-ip>:8000/mcp` and add the `X-API-Key` header where noted.

### VS Code (Copilot)

Add to `settings.json` (`Ctrl+Shift+P` → "Preferences: Open User Settings (JSON)"), or `.vscode/mcp.json` for per-workspace:

```json
{
  "mcp": {
    "servers": {
      "voron": { "type": "http", "url": "https://printer.example.com/mcp" }
    }
  }
}
```

Without a proxy, add `"headers": { "X-API-Key": "your-api-key-here" }`. Register multiple printers as additional named servers, then address by name in Copilot Chat: `@voron what's your status?`.

### Claude Desktop

The "Add custom connector" UI only accepts OAuth 2.1 + PKCE; klipper-mcp uses a static `X-API-Key`, so that UI fails with a sign-in error. Workaround: [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) as a **stdio shim** (Claude Desktop trusts local subprocesses without OAuth).

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows), creating it if needed:

```json
{
  "mcpServers": {
    "voron": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://printer.example.com/mcp"]
    }
  }
}
```

Without a proxy, pass the key with `--header` (the `${VAR}` form dodges a Claude Desktop quoting bug):

```json
{
  "mcpServers": {
    "voron": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://192.168.x.x:8000/mcp", "--header", "X-API-Key:${API_KEY}"],
      "env": { "API_KEY": "your-api-key-here" }
    }
  }
}
```

**Restart Claude Desktop completely** (⌘Q, not reload) — stdio MCPs spawn at launch. First run installs `mcp-remote` via `npx` (10–20s) and needs Node.js (`brew install node`). Debug logs: `~/.mcp-auth/<server_hash>_debug.log`.

### Claude Code

Native HTTP MCP support with custom headers, no shim:

```bash
# With reverse proxy
claude mcp add --transport http voron https://printer.example.com/mcp

# Without — pass the key as a header
claude mcp add --transport http voron http://192.168.x.x:8000/mcp \
  --header "X-API-Key: your-api-key-here"
```

Confirm with `claude mcp list`, then start a new session.

### Smoke test

Ask any client: *"What's the voron's printer status?"* A working setup returns temps, position, homed axes, and the last job. If not:

- Pi reachable: `ping <pi-host>`
- Proxy responds: `curl -v https://printer.example.com/health`
- Server up: `sudo systemctl status klipper-mcp`
- Firewall allows the port (8000 direct, 443 proxied)
- API key matches in `config.py` / client config

## Security

| Gate | What it does |
| ---- | ------------ |
| **`API_KEY`** | Every request must send a matching `X-API-Key` header. |
| **`ARMED`** | `True` required for dangerous ops (G-code, temp changes). |
| **`READ_ONLY`** | `True` **unregisters every write tool at startup** — they can't be called regardless of `ARMED`/`ADMIN_PIN`. Overrides `ARMED`. |
| **`ADMIN_PIN`** | Required for destructive ops (file delete, config restore, reboot). |
| **Audit log** | All operations logged to `data/audit.log`. |

`READ_ONLY=True` keeps every read/analysis tool (status, temps, logs, mesh, history, snapshots, diagnostics) and blocks all writes: motion/print control, temp changes, file writes/deletes, system changes, hardware tuning, notifications, Spoolman/timelapse changes. The startup log and status page (`/`) show registered vs. blocked counts.

> **Adding a tool?** If it changes state, mark it `@mcp.tool(write=True)` so `READ_ONLY` excludes it. Read-only tools use `@mcp.tool()`.

## Usage

Talk to the printer in natural language. Examples:

```text
"What's my printer's current status?"
"Set the bed to 60°C and hotend to 210°C"
"Start printing benchy.gcode"
"Pick up T1" / "Drop the current tool"
"Audit my Voron's configuration"
"Analyze my temperature data for anomalies"
"Show print statistics and filament usage by material"
"Backup my config, then check for Klipper updates"
"Bulk import filaments into Spoolman from the community database"
```

The agent chains the relevant tools and reports back with temps, diagnostics, tables, or recommendations as appropriate.

## Optional Integrations

**Spoolman** — filament tracking ([Spoolman](https://github.com/Donkie/Spoolman)):

```bash
cd ~/klipper-mcp/scripts && chmod +x install_spoolman.sh && ./install_spoolman.sh
# then set SPOOLMAN_ENABLED=True and SPOOLMAN_URL in config
```

**TMC Autotune** — automatic TMC tuning: [klipper_tmc_autotune](https://github.com/andrewmcgr/klipper_tmc_autotune).

**LED Effects** — animated LEDs: [klipper-led_effect](https://github.com/julianschill/klipper-led_effect).

## Troubleshooting

### Server won't start

```bash
systemctl status moonraker            # is Moonraker running?
journalctl -u klipper-mcp -f          # check logs
python3 -c "import config; print(config.MOONRAKER_URL)"   # verify config
```

### Can't connect from a client

Verify Pi IP, open port 8000 (`sudo ufw allow 8000`), confirm API key matches, test `curl -H "X-API-Key: your-key" http://ip:8000/health`.

### Operations failing

Check `ARMED=True`, confirm Klipper is ready (`systemctl status klipper`), tail `~/printer_data/logs/klippy.log`.

### Spoolman not working

`systemctl status spoolman`, confirm `SPOOLMAN_URL`, test `curl http://localhost:7912/api/v1/health`.

## Project Structure

```text
klipper-mcp/
├── server.py            # Main MCP server
├── moonraker.py         # Moonraker API client
├── config.py            # Configuration
├── install.sh           # Installer
├── klipper-mcp.service  # Systemd unit
├── tools/               # Tool implementations (printer, toolchanger, tmc,
│                        #   led_effects, filesystem, camera, statistics,
│                        #   diagnostics, temperature, spoolman, notifications,
│                        #   backup, gcode_analysis, system)
├── data/                # Runtime: audit.log, maintenance.json
├── backups/             # Config backups
├── scenes/              # LED scene presets
└── docs/                # Documentation
```

## Contributing

Fork, branch, add tests if applicable, open a PR.

## License

MIT — see LICENSE.

## Acknowledgments

[Klipper](https://www.klipper3d.org/) · [Moonraker](https://moonraker.readthedocs.io/) · [Model Context Protocol](https://modelcontextprotocol.io/) · [StealthChanger](https://github.com/DraftShift/StealthChanger) · [Spoolman](https://github.com/Donkie/Spoolman)
