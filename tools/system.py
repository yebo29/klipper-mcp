"""
System Management Tools
Software updates, service control, system monitoring
"""

import json
import os
import subprocess
from typing import Optional
import config
from moonraker import get_client


def register_system_tools(mcp):
    """Register system management tools."""

    @mcp.tool()
    async def get_system_info() -> str:
        """
        Get system information including CPU, memory, disk usage, and uptime.
        """
        import platform

        info = {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        }

        # CPU info
        try:
            with open("/proc/loadavg", "r") as f:
                load = f.read().split()
                info["load_average"] = {
                    "1min": float(load[0]),
                    "5min": float(load[1]),
                    "15min": float(load[2]),
                }
        except:
            pass

        # Memory info
        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip().split()[0]
                        meminfo[key] = int(value)

                total = meminfo.get("MemTotal", 0) / 1024  # MB
                free = meminfo.get("MemFree", 0) / 1024
                available = meminfo.get("MemAvailable", 0) / 1024
                buffers = meminfo.get("Buffers", 0) / 1024
                cached = meminfo.get("Cached", 0) / 1024

                info["memory"] = {
                    "total_mb": round(total, 1),
                    "available_mb": round(available, 1),
                    "used_mb": round(total - available, 1),
                    "percent_used": (
                        round((total - available) / total * 100, 1) if total > 0 else 0
                    ),
                }
        except:
            pass

        # Disk usage
        try:
            statvfs = os.statvfs("/")
            total = statvfs.f_blocks * statvfs.f_frsize / (1024**3)  # GB
            free = statvfs.f_bfree * statvfs.f_frsize / (1024**3)
            used = total - free

            info["disk"] = {
                "total_gb": round(total, 2),
                "used_gb": round(used, 2),
                "free_gb": round(free, 2),
                "percent_used": round(used / total * 100, 1) if total > 0 else 0,
            }
        except:
            pass

        # Uptime
        try:
            with open("/proc/uptime", "r") as f:
                uptime_seconds = float(f.read().split()[0])
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                info["uptime"] = {
                    "seconds": int(uptime_seconds),
                    "formatted": f"{days}d {hours}h {minutes}m",
                }
        except:
            pass

        # CPU temperature
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read().strip()) / 1000
                info["cpu_temp_c"] = round(temp, 1)
        except:
            pass

        return json.dumps(info, indent=2)

    @mcp.tool()
    async def get_network_info() -> str:
        """
        Get network information including IP addresses, hostname, and connection status.
        """
        import socket

        info = {"hostname": socket.gethostname(), "interfaces": {}}

        # Get IP addresses
        try:
            result = subprocess.run(
                ["ip", "-j", "addr"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                import json as j

                interfaces = j.loads(result.stdout)
                for iface in interfaces:
                    name = iface.get("ifname", "")
                    if name in ["lo"]:
                        continue
                    addrs = []
                    for addr_info in iface.get("addr_info", []):
                        if addr_info.get("family") == "inet":
                            addrs.append(addr_info.get("local"))
                    if addrs:
                        info["interfaces"][name] = {
                            "ip_addresses": addrs,
                            "state": iface.get("operstate", "unknown"),
                        }
        except:
            # Fallback method
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                info["primary_ip"] = s.getsockname()[0]
                s.close()
            except:
                pass

        # WiFi signal strength (if applicable)
        try:
            result = subprocess.run(
                ["iwconfig"], capture_output=True, text=True, timeout=5
            )
            if "Signal level" in result.stdout:
                for line in result.stdout.split("\n"):
                    if "Signal level" in line:
                        # Extract signal level
                        import re

                        match = re.search(r"Signal level[=:](-?\d+)", line)
                        if match:
                            info["wifi_signal_dbm"] = int(match.group(1))
                        break
        except:
            pass

        return json.dumps(info, indent=2)

    @mcp.tool()
    async def check_updates() -> str:
        """
        Check for available software updates for Klipper, Moonraker, and system.
        Uses Moonraker's update manager API.
        """
        client = get_client()
        session = await client._get_session()

        try:
            # Get update status from Moonraker
            url = f"{client.base_url}/machine/update/status"
            async with session.get(url, params={"refresh": "false"}) as response:
                if response.status != 200:
                    return json.dumps(
                        {"error": f"Failed to get update status: {response.status}"}
                    )

                data = await response.json()
                result = data.get("result", {})

                updates = {"busy": result.get("busy", False), "components": {}}

                version_info = result.get("version_info", {})
                for component, info in version_info.items():
                    comp_data = {
                        "version": info.get("version", "unknown"),
                        "remote_version": info.get("remote_version", "unknown"),
                        "is_valid": info.get("is_valid", False),
                        "is_dirty": info.get("is_dirty", False),
                    }

                    # Check if update available
                    current = info.get("version", "")
                    remote = info.get("remote_version", "")
                    if current and remote and current != remote:
                        comp_data["update_available"] = True
                    else:
                        comp_data["update_available"] = False

                    # Add commit info if available
                    if "commits_behind" in info:
                        comp_data["commits_behind"] = info["commits_behind"]

                    updates["components"][component] = comp_data

                # Summary
                updates_available = [
                    k
                    for k, v in updates["components"].items()
                    if v.get("update_available")
                ]
                updates["summary"] = {
                    "updates_available": len(updates_available),
                    "components_with_updates": updates_available,
                }

                return json.dumps(updates, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(write=True)
    async def update_component(component: str) -> str:
        """
        Update a specific software component (klipper, moonraker, etc.).

        Args:
            component: Component to update - 'klipper', 'moonraker', 'mainsail', 'fluidd', 'system', or 'all'
        """
        client = get_client()
        session = await client._get_session()

        valid_components = [
            "klipper",
            "moonraker",
            "mainsail",
            "fluidd",
            "klipperscreen",
            "system",
        ]

        if component.lower() == "all":
            # Update all components
            try:
                url = f"{client.base_url}/machine/update/full"
                async with session.post(url) as response:
                    if response.status != 200:
                        return json.dumps(
                            {"error": f"Failed to start full update: {response.status}"}
                        )
                    return json.dumps(
                        {
                            "status": "started",
                            "message": "Full system update started. This may take several minutes.",
                            "note": "Services will restart automatically. Monitor via Moonraker logs.",
                        },
                        indent=2,
                    )
            except Exception as e:
                return json.dumps({"error": str(e)})

        if component.lower() not in valid_components:
            return json.dumps(
                {
                    "error": f"Unknown component: {component}",
                    "valid_components": valid_components + ["all"],
                }
            )

        try:
            url = f"{client.base_url}/machine/update/client"
            params = {"name": component.lower()}

            if component.lower() in ["klipper", "moonraker"]:
                url = f"{client.base_url}/machine/update/{component.lower()}"
                params = {}
            elif component.lower() == "system":
                url = f"{client.base_url}/machine/update/system"
                params = {}

            async with session.post(url, params=params if params else None) as response:
                if response.status != 200:
                    text = await response.text()
                    return json.dumps(
                        {
                            "error": f"Failed to update {component}: {response.status} - {text}"
                        }
                    )

                return json.dumps(
                    {
                        "status": "started",
                        "component": component,
                        "message": f"Update for {component} started. Check Moonraker logs for progress.",
                        "note": "Service may restart automatically.",
                    },
                    indent=2,
                )

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(write=True)
    async def refresh_update_status() -> str:
        """
        Refresh the update status by checking remote repositories.
        This fetches the latest version information from GitHub/repos.
        """
        client = get_client()
        session = await client._get_session()

        try:
            url = f"{client.base_url}/machine/update/status"
            async with session.get(url, params={"refresh": "true"}) as response:
                if response.status != 200:
                    return json.dumps(
                        {"error": f"Failed to refresh: {response.status}"}
                    )

                return json.dumps(
                    {
                        "status": "refreshed",
                        "message": "Update status refreshed. Use check_updates to see results.",
                    },
                    indent=2,
                )

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def get_service_status(service: str = "all") -> str:
        """
        Get the status of printer-related services.

        Args:
            service: Service name or 'all' for all services (default: all)
        """
        allowed_services = [
            "klipper",
            "moonraker",
            "KlipperScreen",
            "crowsnest",
            "klipper-mcp",
        ]

        if service.lower() == "all":
            services = allowed_services
        else:
            # Match case-insensitively but run the canonical systemd unit name
            canonical = next(
                (s for s in allowed_services if s.lower() == service.lower()), None
            )
            if canonical is None:
                return json.dumps(
                    {
                        "error": f"Service '{service}' not in allowlist",
                        "allowed_services": allowed_services,
                    }
                )
            services = [canonical]

        results = {}

        for svc in services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", svc],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                status = result.stdout.strip()

                # Get more details
                result2 = subprocess.run(
                    [
                        "systemctl",
                        "show",
                        svc,
                        "--property=ActiveState,SubState,MainPID",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                props = {}
                for line in result2.stdout.strip().split("\n"):
                    if "=" in line:
                        k, v = line.split("=", 1)
                        props[k] = v

                results[svc] = {
                    "status": status,
                    "active_state": props.get("ActiveState", "unknown"),
                    "sub_state": props.get("SubState", "unknown"),
                    "pid": props.get("MainPID", "0"),
                }
            except Exception as e:
                results[svc] = {"error": str(e)}

        return json.dumps(results, indent=2)

    @mcp.tool(write=True)
    async def restart_service(service: str) -> str:
        """
        Restart a printer-related service.

        Args:
            service: Service to restart - 'klipper', 'moonraker', 'KlipperScreen', 'crowsnest'
        """
        allowed_services = [
            "klipper",
            "moonraker",
            "KlipperScreen",
            "crowsnest",
            "klipper-mcp",
        ]

        if service not in allowed_services:
            return json.dumps(
                {
                    "error": f"Service '{service}' not allowed",
                    "allowed_services": allowed_services,
                }
            )

        try:
            result = subprocess.run(
                ["sudo", "systemctl", "restart", service],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return json.dumps(
                    {"error": f"Failed to restart {service}", "stderr": result.stderr}
                )

            # Check new status
            result2 = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=5,
            )

            return json.dumps(
                {
                    "status": "restarted",
                    "service": service,
                    "new_state": result2.stdout.strip(),
                    "message": f"{service} has been restarted",
                },
                indent=2,
            )

        except subprocess.TimeoutExpired:
            return json.dumps({"error": f"Timeout restarting {service}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(write=True)
    async def reboot_system(delay_seconds: int = 60) -> str:
        """
        Reboot the host system.

        Args:
            delay_seconds: Delay before reboot in seconds, rounded to the nearest
                minute (.5 rounds up). Scheduled delay is at least 1 minute.
        """
        if not config.ARMED:
            return json.dumps(
                {"error": "System reboot requires ARMED=True in config", "armed": False}
            )

        if delay_seconds < 0:
            return json.dumps(
                {
                    "error": "delay_seconds must be non-negative",
                    "delay_seconds": delay_seconds,
                }
            )

        # Round to the nearest minute, .5 rounding up (shutdown takes whole
        # minutes). Integer arithmetic avoids round()'s banker's rounding, which
        # rounds tie values (e.g. 150s) to an even minute and scheduled sooner.
        delay_minutes = max(1, (delay_seconds + 30) // 60)

        try:
            subprocess.Popen(
                [
                    "sudo",
                    "shutdown",
                    "-r",
                    f"+{delay_minutes}",
                    "Reboot requested via MCP",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            return json.dumps(
                {
                    "status": "scheduled",
                    "message": f"System will reboot in approximately {delay_minutes} minute(s)",
                    "warning": "All services will be unavailable during reboot",
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(write=True)
    async def shutdown_system(delay_seconds: int = 60) -> str:
        """
        Shutdown the host system.

        Args:
            delay_seconds: Delay before shutdown in seconds, rounded to the nearest
                minute (.5 rounds up). Scheduled delay is at least 1 minute.
        """
        if not config.ARMED:
            return json.dumps(
                {
                    "error": "System shutdown requires ARMED=True in config",
                    "armed": False,
                }
            )

        if delay_seconds < 0:
            return json.dumps(
                {
                    "error": "delay_seconds must be non-negative",
                    "delay_seconds": delay_seconds,
                }
            )

        # Round to the nearest minute, .5 rounding up (shutdown takes whole
        # minutes). Integer arithmetic avoids round()'s banker's rounding, which
        # rounds tie values (e.g. 150s) to an even minute and scheduled sooner.
        delay_minutes = max(1, (delay_seconds + 30) // 60)

        try:
            subprocess.Popen(
                [
                    "sudo",
                    "shutdown",
                    "-h",
                    f"+{delay_minutes}",
                    "Shutdown requested via MCP",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            return json.dumps(
                {
                    "status": "scheduled",
                    "message": f"System will shut down in approximately {delay_minutes} minute(s)",
                    "warning": "You will need physical access to power on again",
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def get_moonraker_config() -> str:
        """
        Get the current Moonraker configuration including enabled components.
        """
        client = get_client()
        session = await client._get_session()

        try:
            url = f"{client.base_url}/server/info"
            async with session.get(url) as response:
                if response.status != 200:
                    return json.dumps(
                        {"error": f"Failed to get server info: {response.status}"}
                    )

                data = await response.json()
                result = data.get("result", {})

                return json.dumps(
                    {
                        "klippy_connected": result.get("klippy_connected"),
                        "klippy_state": result.get("klippy_state"),
                        "components": result.get("components", []),
                        "failed_components": result.get("failed_components", []),
                        "registered_directories": result.get(
                            "registered_directories", []
                        ),
                        "warnings": result.get("warnings", []),
                        "moonraker_version": result.get("moonraker_version"),
                        "api_version": result.get("api_version"),
                        "api_version_string": result.get("api_version_string"),
                    },
                    indent=2,
                )

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def get_printer_objects() -> str:
        """
        List all available printer objects that can be queried.
        Useful for discovering what data is available from Klipper.
        """
        client = get_client()
        session = await client._get_session()

        try:
            url = f"{client.base_url}/printer/objects/list"
            async with session.get(url) as response:
                if response.status != 200:
                    return json.dumps(
                        {"error": f"Failed to get objects: {response.status}"}
                    )

                data = await response.json()
                objects = data.get("result", {}).get("objects", [])

                # Categorize objects
                categories = {
                    "heaters": [],
                    "fans": [],
                    "steppers": [],
                    "sensors": [],
                    "leds": [],
                    "tools": [],
                    "system": [],
                    "other": [],
                }

                for obj in sorted(objects):
                    obj_lower = obj.lower()
                    if "heater" in obj_lower or "extruder" in obj_lower:
                        categories["heaters"].append(obj)
                    elif "fan" in obj_lower:
                        categories["fans"].append(obj)
                    elif "stepper" in obj_lower or "tmc" in obj_lower:
                        categories["steppers"].append(obj)
                    elif "sensor" in obj_lower or "probe" in obj_lower:
                        categories["sensors"].append(obj)
                    elif "led" in obj_lower or "neopixel" in obj_lower:
                        categories["leds"].append(obj)
                    elif obj.startswith("tool") or obj.startswith("T"):
                        categories["tools"].append(obj)
                    elif obj in [
                        "mcu",
                        "webhooks",
                        "print_stats",
                        "toolhead",
                        "gcode_move",
                        "motion_report",
                    ]:
                        categories["system"].append(obj)
                    else:
                        categories["other"].append(obj)

                return json.dumps(
                    {"total_objects": len(objects), "categories": categories}, indent=2
                )

        except Exception as e:
            return json.dumps({"error": str(e)})
