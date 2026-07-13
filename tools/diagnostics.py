"""
Diagnostics Tools
Error log parsing, config validation, and troubleshooting
"""

import json
import re
import config
from moonraker import get_client

# Klipper runtime log lines start with a timestamp or the !! error prefix.
# Config-dump lines (e.g. "max_error = 30") have neither, so this pattern
# lets us skip false positives from the startup config section.
_RUNTIME_LINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

# Cap how much of a log file we download in one call (2 MB)
_MAX_LOG_BYTES = 2 * 1024 * 1024


async def _read_log_tail(response) -> str:
    """Return the last _MAX_LOG_BYTES of a response body as text.

    Streams the body and keeps only a rolling tail buffer, so a very large
    klippy.log is never fully held in memory (important on low-RAM SBCs). When
    the log is larger than the cap, the leading partial line is dropped.
    """
    tail = bytearray()
    truncated = False
    async for chunk in response.content.iter_chunked(65536):
        tail += chunk
        if len(tail) > _MAX_LOG_BYTES:
            del tail[:-_MAX_LOG_BYTES]
            truncated = True
    if truncated:
        first_nl = tail.find(b"\n")
        if first_nl >= 0:
            del tail[: first_nl + 1]
    return tail.decode("utf-8", errors="replace")


def register_diagnostics_tools(mcp):
    """Register diagnostics tools."""

    @mcp.tool()
    async def parse_klippy_log(lines: int = 200) -> str:
        """
        Parse klippy.log for errors, warnings, and important messages.

        Args:
            lines: Number of recent lines to analyze (default: 200)
        """
        client = get_client()
        session = await client._get_session()

        url = f"{client.base_url}/server/files/logs/klippy.log"

        try:
            async with session.get(url) as response:
                if response.status == 404:
                    return json.dumps({"error": "klippy.log not found"})
                response.raise_for_status()
                content = await _read_log_tail(response)

                # Get last N lines
                all_lines = content.split("\n")
                recent_lines = (
                    all_lines[-lines:] if len(all_lines) > lines else all_lines
                )

                errors = []
                warnings = []
                shutdowns = []
                tmc_errors = []
                mcu_issues = []

                for i, line in enumerate(recent_lines):
                    line_lower = line.lower()
                    is_runtime = _RUNTIME_LINE_RE.match(line) or line.startswith("!!")

                    # Errors (runtime lines only to avoid config-dump false positives)
                    if is_runtime and (
                        "error" in line_lower or "exception" in line_lower
                    ):
                        errors.append(
                            {
                                "line": len(all_lines) - len(recent_lines) + i + 1,
                                "text": line.strip(),
                            }
                        )

                    # Warnings
                    elif is_runtime and (
                        "warning" in line_lower or "warn" in line_lower
                    ):
                        warnings.append(
                            {
                                "line": len(all_lines) - len(recent_lines) + i + 1,
                                "text": line.strip(),
                            }
                        )

                    # Shutdown events (no runtime guard — shutdown lines may lack a timestamp)
                    elif "shutdown" in line_lower:
                        shutdowns.append(
                            {
                                "line": len(all_lines) - len(recent_lines) + i + 1,
                                "text": line.strip(),
                            }
                        )

                    # TMC driver issues
                    elif (
                        is_runtime
                        and "tmc" in line_lower
                        and (
                            "fault" in line_lower
                            or "error" in line_lower
                            or "overtemp" in line_lower
                        )
                    ):
                        tmc_errors.append(
                            {
                                "line": len(all_lines) - len(recent_lines) + i + 1,
                                "text": line.strip(),
                            }
                        )

                    # MCU issues
                    elif (
                        is_runtime
                        and "mcu" in line_lower
                        and (
                            "timeout" in line_lower
                            or "disconnect" in line_lower
                            or "lost" in line_lower
                        )
                    ):
                        mcu_issues.append(
                            {
                                "line": len(all_lines) - len(recent_lines) + i + 1,
                                "text": line.strip(),
                            }
                        )

                return json.dumps(
                    {
                        "analyzed_lines": len(recent_lines),
                        "summary": {
                            "errors": len(errors),
                            "warnings": len(warnings),
                            "shutdowns": len(shutdowns),
                            "tmc_errors": len(tmc_errors),
                            "mcu_issues": len(mcu_issues),
                        },
                        "errors": errors[-10:] if errors else [],  # Last 10
                        "warnings": warnings[-5:] if warnings else [],  # Last 5
                        "shutdowns": shutdowns[-3:] if shutdowns else [],  # Last 3
                        "tmc_errors": tmc_errors[-5:] if tmc_errors else [],
                        "mcu_issues": mcu_issues[-5:] if mcu_issues else [],
                    },
                    indent=2,
                )

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def get_recent_errors(count: int = 10) -> str:
        """
        Get the most recent errors from klippy.log with context.

        Args:
            count: Number of errors to return (default: 10)
        """
        client = get_client()
        session = await client._get_session()

        url = f"{client.base_url}/server/files/logs/klippy.log"

        try:
            async with session.get(url) as response:
                if response.status == 404:
                    return json.dumps({"error": "klippy.log not found"})
                response.raise_for_status()
                content = await _read_log_tail(response)

                lines = content.split("\n")

                errors_with_context = []

                for i, line in enumerate(lines):
                    is_runtime = _RUNTIME_LINE_RE.match(line) or line.startswith("!!")
                    if not is_runtime:
                        continue
                    if "error" in line.lower() or "exception" in line.lower():
                        # Get context: 2 lines before and 2 after
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        context = lines[start:end]

                        errors_with_context.append(
                            {
                                "line_number": i + 1,
                                "error": line.strip(),
                                "context": [ln.strip() for ln in context],
                            }
                        )

                # Return last N errors
                recent_errors = (
                    errors_with_context[-count:] if errors_with_context else []
                )

                return json.dumps(
                    {
                        "total_errors_found": len(errors_with_context),
                        "showing": len(recent_errors),
                        "errors": recent_errors,
                    },
                    indent=2,
                )

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def check_common_issues() -> str:
        """
        Check for common configuration issues and problems.
        Analyzes printer state and recent logs for known issues.
        """
        client = get_client()
        issues = []
        warnings = []

        # Check printer status
        status_result = await client.get_printer_status()
        if "error" in status_result:
            issues.append(
                {
                    "category": "connection",
                    "severity": "critical",
                    "message": "Cannot connect to Klipper",
                    "suggestion": "Check if Klipper service is running",
                }
            )
            return json.dumps({"issues": issues, "warnings": warnings})

        status = status_result.get("result", {}).get("status", {})

        # Check print state
        print_stats = status.get("print_stats", {})
        if print_stats.get("state") == "error":
            issues.append(
                {
                    "category": "print",
                    "severity": "high",
                    "message": f"Printer in error state: {print_stats.get('message', 'unknown')}",
                    "suggestion": "Check klippy.log for details and restart Klipper",
                }
            )

        # Check temperatures
        extruder = status.get("extruder", {})
        if extruder.get("temperature", 0) > 50 and extruder.get("target", 0) == 0:
            warnings.append(
                {
                    "category": "temperature",
                    "message": "Extruder is hot but target is 0",
                    "suggestion": "Extruder may still be cooling down from previous print",
                }
            )

        bed = status.get("heater_bed", {})
        if bed.get("temperature", 0) > 50 and bed.get("target", 0) == 0:
            warnings.append(
                {
                    "category": "temperature",
                    "message": "Bed is hot but target is 0",
                    "suggestion": "Bed may still be cooling down",
                }
            )

        # Check homing
        toolhead = status.get("toolhead", {})
        homed = toolhead.get("homed_axes", "")
        if homed != "xyz":
            warnings.append(
                {
                    "category": "homing",
                    "message": f"Not all axes homed (current: {homed or 'none'})",
                    "suggestion": "Run G28 to home all axes before printing",
                }
            )

        # Check for idle timeout
        idle = status.get("idle_timeout", {})
        if idle.get("state") == "Printing" and print_stats.get("state") != "printing":
            warnings.append(
                {
                    "category": "state",
                    "message": "Idle timeout thinks printer is printing but print_stats disagrees",
                    "suggestion": "State may be out of sync - consider FIRMWARE_RESTART",
                }
            )

        return json.dumps(
            {
                "issues_found": len(issues),
                "warnings_found": len(warnings),
                "issues": issues,
                "warnings": warnings,
                "status": "healthy" if not issues else "needs_attention",
            },
            indent=2,
        )

    @mcp.tool()
    async def get_mcu_status() -> str:
        """
        Get MCU (microcontroller) status including timing and connection info.
        """
        client = get_client()

        result = await client.query_printer_objects(
            {
                "mcu": [
                    "mcu_version",
                    "mcu_build_versions",
                    "mcu_constants",
                    "last_stats",
                ],
                "toolhead": ["max_velocity", "max_accel", "square_corner_velocity"],
            }
        )

        if "error" in result:
            return json.dumps({"error": result["error"]})

        status = result.get("result", {}).get("status", {})

        mcu = status.get("mcu", {})
        toolhead = status.get("toolhead", {})

        return json.dumps(
            {
                "mcu": {
                    "version": mcu.get("mcu_version"),
                    "build_versions": mcu.get("mcu_build_versions"),
                    "last_stats": mcu.get("last_stats"),
                },
                "motion": {
                    "max_velocity": toolhead.get("max_velocity"),
                    "max_accel": toolhead.get("max_accel"),
                    "square_corner_velocity": toolhead.get("square_corner_velocity"),
                },
            },
            indent=2,
        )

    @mcp.tool()
    async def get_gcode_history(count: int = 50) -> str:
        """
        Get recent G-code commands and responses.

        Args:
            count: Number of recent commands to return (default: 50)
        """
        client = get_client()
        result = await client.get_gcode_store(count=count)

        if "error" in result:
            return json.dumps({"error": result["error"]})

        gcode_store = result.get("result", {}).get("gcode_store", [])

        commands = []
        for entry in gcode_store[-count:]:
            commands.append(
                {
                    "message": entry.get("message"),
                    "time": entry.get("time"),
                    "type": entry.get("type"),
                }
            )

        return json.dumps({"count": len(commands), "commands": commands}, indent=2)

    @mcp.tool()
    async def diagnose_problem(symptom: str) -> str:
        """
        Get troubleshooting suggestions based on a symptom description.

        Args:
            symptom: Description of the problem (e.g., 'layer shifts', 'nozzle clog', 'bed adhesion')
        """
        symptom_lower = symptom.lower()

        troubleshooting = {
            "layer shift": {
                "possible_causes": [
                    "Belts too loose",
                    "Stepper motor overheating (TMC overtemp)",
                    "Acceleration too high",
                    "Nozzle hitting print",
                    "Grub screws loose on pulleys",
                ],
                "suggestions": [
                    "Check belt tension",
                    "Check TMC driver temps (run parse_klippy_log)",
                    "Reduce max_accel in printer.cfg",
                    "Check for Z-hop in slicer",
                    "Tighten grub screws on motor pulleys",
                ],
                "gcode_commands": ["M569 (check TMC)", "SET_VELOCITY_LIMIT ACCEL=3000"],
            },
            "adhesion": {
                "possible_causes": [
                    "Bed not level",
                    "Z offset too high",
                    "Bed not clean",
                    "Bed temp too low",
                    "First layer speed too fast",
                ],
                "suggestions": [
                    "Run bed mesh calibration",
                    "Adjust Z offset (negative = closer)",
                    "Clean bed with IPA",
                    "Increase bed temp by 5-10°C",
                    "Reduce first layer speed to 20mm/s",
                ],
            },
            "clog": {
                "possible_causes": [
                    "Heat creep",
                    "Partial clog from debris",
                    "Wet filament",
                    "Gap between nozzle and heatbreak",
                    "Retraction too high",
                ],
                "suggestions": [
                    "Check hotend fan is working",
                    "Do cold pull to clear partial clog",
                    "Dry filament (4h at 50-60°C)",
                    "Re-seat nozzle hot-tightened",
                    "Reduce retraction distance",
                ],
            },
            "stringing": {
                "possible_causes": [
                    "Retraction too low",
                    "Temperature too high",
                    "Wet filament",
                    "Travel speed too slow",
                ],
                "suggestions": [
                    "Increase retraction distance/speed",
                    "Lower hotend temp by 5-10°C",
                    "Dry filament",
                    "Increase travel speed",
                ],
            },
            "underextrusion": {
                "possible_causes": [
                    "Partial clog",
                    "Extruder tension too low",
                    "Incorrect e-steps",
                    "Filament grinding",
                    "PTFE tube gap",
                ],
                "suggestions": [
                    "Check for clog (cold pull)",
                    "Increase extruder gear tension",
                    "Calibrate e-steps",
                    "Check extruder gear for worn teeth",
                    "Check PTFE tube seating",
                ],
            },
        }

        # Find matching symptom
        matched = None
        for key in troubleshooting:
            if key in symptom_lower:
                matched = troubleshooting[key]
                matched["symptom"] = key
                break

        if matched:
            return json.dumps(matched, indent=2)
        else:
            return json.dumps(
                {
                    "message": f"No specific troubleshooting found for '{symptom}'",
                    "available_topics": list(troubleshooting.keys()),
                    "suggestion": "Try describing the symptom differently or check klippy.log for errors",
                },
                indent=2,
            )

    @mcp.tool()
    async def get_log_files() -> str:
        """
        List all log files with their sizes and ages.
        Returns information about klippy.log, moonraker.log, and other logs.
        """
        import os
        from datetime import datetime

        logs_path = config.LOGS_PATH

        if not os.path.exists(logs_path):
            return json.dumps({"error": f"Logs directory not found: {logs_path}"})

        log_files = []
        total_size = 0

        for filename in sorted(os.listdir(logs_path)):
            filepath = os.path.join(logs_path, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                size_mb = stat.st_size / (1024 * 1024)
                total_size += stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime)

                log_files.append(
                    {
                        "name": filename,
                        "size_bytes": stat.st_size,
                        "size_mb": round(size_mb, 2),
                        "modified": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                        "age_days": (datetime.now() - mtime).days,
                    }
                )

        return json.dumps(
            {
                "logs_path": logs_path,
                "total_files": len(log_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "files": log_files,
            },
            indent=2,
        )

    @mcp.tool(write=True)
    async def clear_old_logs(days_to_keep: int = 7, dry_run: bool = True) -> str:
        """
        Clear log files older than specified days.

        Args:
            days_to_keep: Keep logs from the last N days (default: 7)
            dry_run: If True, only show what would be deleted without actually deleting (default: True)
        """
        import os
        from datetime import datetime, timedelta

        logs_path = config.LOGS_PATH

        if not os.path.exists(logs_path):
            return json.dumps({"error": f"Logs directory not found: {logs_path}"})

        cutoff = datetime.now() - timedelta(days=days_to_keep)

        to_delete = []
        kept = []
        total_freed = 0

        # Protected files that should never be deleted (current active logs)
        protected = [
            "klippy.log",
            "moonraker.log",
            "crowsnest.log",
            "KlipperScreen.log",
            "octoeverywhere.log",
        ]

        for filename in os.listdir(logs_path):
            filepath = os.path.join(logs_path, filename)
            if not os.path.isfile(filepath):
                continue

            stat = os.stat(filepath)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            size_mb = stat.st_size / (1024 * 1024)

            # Keep protected (current) log files
            if filename in protected:
                kept.append(
                    {
                        "name": filename,
                        "reason": "active log",
                        "size_mb": round(size_mb, 2),
                    }
                )
                continue

            # Check if older than cutoff
            if mtime < cutoff:
                to_delete.append(
                    {
                        "name": filename,
                        "size_mb": round(size_mb, 2),
                        "modified": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
                total_freed += stat.st_size

                if not dry_run:
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        to_delete[-1]["error"] = str(e)
            else:
                kept.append(
                    {
                        "name": filename,
                        "reason": "within retention",
                        "size_mb": round(size_mb, 2),
                    }
                )

        return json.dumps(
            {
                "dry_run": dry_run,
                "days_to_keep": days_to_keep,
                "cutoff_date": cutoff.strftime("%Y-%m-%d"),
                "files_to_delete": len(to_delete),
                "space_freed_mb": round(total_freed / (1024 * 1024), 2),
                "deleted": to_delete,
                "kept": kept,
                "message": (
                    "Dry run - no files deleted. Set dry_run=false to delete."
                    if dry_run
                    else f"Deleted {len(to_delete)} files"
                ),
            },
            indent=2,
        )

    @mcp.tool(write=True)
    async def truncate_log(log_name: str = "klippy", keep_lines: int = 1000) -> str:
        """
        Truncate a log file keeping only the most recent lines.
        Useful for reducing klippy.log size while keeping recent data.

        Args:
            log_name: Log file to truncate - 'klippy', 'moonraker', or 'klipper_screen' (default: klippy)
            keep_lines: Number of recent lines to keep (default: 1000)
        """
        import os

        log_map = {
            "klippy": "klippy.log",
            "moonraker": "moonraker.log",
            "klipper_screen": "KlipperScreen.log",
            "crowsnest": "crowsnest.log",
            "octoeverywhere": "octoeverywhere.log",
        }

        if log_name not in log_map:
            return json.dumps(
                {
                    "error": f"Unknown log: {log_name}",
                    "available_logs": list(log_map.keys()),
                }
            )

        filepath = os.path.join(config.LOGS_PATH, log_map[log_name])

        if not os.path.exists(filepath):
            return json.dumps({"error": f"Log file not found: {filepath}"})

        # Get original size
        original_size = os.path.getsize(filepath)

        try:
            # Read all lines
            with open(filepath, "r", errors="replace") as f:
                lines = f.readlines()

            original_lines = len(lines)

            # Keep only last N lines
            if len(lines) > keep_lines:
                lines = lines[-keep_lines:]

            # Write back
            with open(filepath, "w") as f:
                f.writelines(lines)

            new_size = os.path.getsize(filepath)

            return json.dumps(
                {
                    "log_file": log_map[log_name],
                    "original_lines": original_lines,
                    "kept_lines": len(lines),
                    "lines_removed": original_lines - len(lines),
                    "original_size_mb": round(original_size / (1024 * 1024), 2),
                    "new_size_mb": round(new_size / (1024 * 1024), 2),
                    "space_freed_mb": round(
                        (original_size - new_size) / (1024 * 1024), 2
                    ),
                    "status": "success",
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def get_log_summary() -> str:
        """
        Get a summary of recent log activity - errors, warnings, and events.
        Scans klippy.log, moonraker.log for the last hour of activity.
        """
        import os
        from datetime import datetime

        logs_path = config.LOGS_PATH

        summary = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "period": "last 1 hour",
            "klippy": {"errors": 0, "warnings": 0, "shutdowns": 0},
            "moonraker": {"errors": 0, "warnings": 0, "requests": 0},
            "recent_events": [],
        }

        # Parse klippy.log
        klippy_path = os.path.join(logs_path, "klippy.log")
        if os.path.exists(klippy_path):
            try:
                with open(klippy_path, "r", errors="replace") as f:
                    # Read last 5000 lines for efficiency
                    lines = f.readlines()[-5000:]

                for line in lines:
                    line_lower = line.lower()
                    is_runtime = _RUNTIME_LINE_RE.match(line) or line.startswith("!!")
                    if is_runtime and "error" in line_lower:
                        summary["klippy"]["errors"] += 1
                    elif is_runtime and (
                        "warning" in line_lower or "warn" in line_lower
                    ):
                        summary["klippy"]["warnings"] += 1
                    elif "shutdown" in line_lower:
                        summary["klippy"]["shutdowns"] += 1
                        summary["recent_events"].append(
                            {
                                "source": "klippy",
                                "type": "shutdown",
                                "message": line.strip()[:200],
                            }
                        )
            except Exception as e:
                summary["klippy"]["error"] = str(e)

        # Parse moonraker.log
        moonraker_path = os.path.join(logs_path, "moonraker.log")
        if os.path.exists(moonraker_path):
            try:
                with open(moonraker_path, "r", errors="replace") as f:
                    lines = f.readlines()[-2000:]

                for line in lines:
                    line_lower = line.lower()
                    if "error" in line_lower:
                        summary["moonraker"]["errors"] += 1
                    elif "warning" in line_lower:
                        summary["moonraker"]["warnings"] += 1
                    elif "request" in line_lower:
                        summary["moonraker"]["requests"] += 1
            except Exception as e:
                summary["moonraker"]["error"] = str(e)

        return json.dumps(summary, indent=2)
