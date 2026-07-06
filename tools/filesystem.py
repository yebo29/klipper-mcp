"""
Filesystem Tools
Read, write, list, upload, and delete files on the printer
"""

import json
import os
from typing import Optional
import config
from moonraker import get_client
from ._util import format_duration


def register_filesystem_tools(mcp):
    """Register filesystem tools."""

    @mcp.tool()
    async def list_files(directory: str = "gcodes", recursive: bool = False) -> str:
        """
        List files in a printer directory.

        Args:
            directory: Directory to list - 'gcodes', 'config', 'logs', or full path
            recursive: If True, include subdirectories (default: False)

        Returns list of files with names, sizes, and modification dates.
        """
        client = get_client()

        # Map common names to roots
        root_map = {
            "gcodes": "gcodes",
            "gcode": "gcodes",
            "config": "config",
            "logs": "logs",
        }

        root = root_map.get(directory.lower(), directory)

        result = await client.get_directory(root)

        if "error" in result:
            return json.dumps({"error": result["error"]})

        data = result.get("result", {})

        files = []
        for item in data.get("files", []):
            files.append(
                {
                    "name": item.get("filename"),
                    "size": item.get("size"),
                    "modified": item.get("modified"),
                }
            )

        dirs = []
        for item in data.get("dirs", []):
            dirs.append(
                {
                    "name": item.get("dirname"),
                    "modified": item.get("modified"),
                }
            )

        return json.dumps(
            {
                "directory": root,
                "files": files,
                "subdirectories": dirs,
                "disk_usage": data.get("disk_usage", {}),
            },
            indent=2,
        )

    @mcp.tool()
    async def list_gcode_files() -> str:
        """List all G-code files available for printing."""
        client = get_client()
        result = await client.list_files("gcodes")

        if "error" in result:
            return json.dumps({"error": result["error"]})

        files = result.get("result", [])

        gcode_files = []
        for f in files:
            # API returns 'path' not 'filename'
            fname = f.get("path") or f.get("filename") or "unknown"
            gcode_files.append(
                {
                    "filename": fname,
                    "size_mb": round(f.get("size", 0) / 1024 / 1024, 2),
                    "modified": f.get("modified"),
                }
            )

        # Sort by modified date, newest first
        gcode_files.sort(key=lambda x: x.get("modified", 0), reverse=True)

        return json.dumps({"gcode_files": gcode_files}, indent=2)

    @mcp.tool()
    async def read_file(filepath: str, max_lines: int = 500) -> str:
        """
        Read contents of a file from the printer.

        Args:
            filepath: Path to file relative to printer_data (e.g., 'config/printer.cfg')
            max_lines: Maximum lines to return (default: 500, to avoid huge responses)

        For G-code files, use get_gcode_metadata instead for analysis.
        """
        client = get_client()

        # Determine root and path
        if filepath.startswith("config/"):
            root = "config"
            filename = filepath[7:]  # Remove 'config/'
        elif filepath.startswith("logs/"):
            root = "logs"
            filename = filepath[5:]
        else:
            # Assume config if not specified
            root = "config"
            filename = filepath

        # Use Moonraker's file download endpoint
        session = await client._get_session()
        url = f"{client.base_url}/server/files/{root}/{filename}"

        try:
            async with session.get(url) as response:
                if response.status == 404:
                    return json.dumps({"error": f"File not found: {filepath}"})
                response.raise_for_status()
                content = await response.text()

                # Limit lines
                lines = content.split("\n")
                if len(lines) > max_lines:
                    content = "\n".join(lines[:max_lines])
                    truncated = True
                else:
                    truncated = False

                return json.dumps(
                    {
                        "filepath": filepath,
                        "content": content,
                        "lines": min(len(lines), max_lines),
                        "truncated": truncated,
                        "total_lines": len(lines) if truncated else None,
                    }
                )
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(write=True)
    async def write_file(filepath: str, content: str, pin: str) -> str:
        """
        Write content to a file on the printer.
        REQUIRES: Admin PIN for safety.

        Args:
            filepath: Path relative to config directory (e.g., 'macros/custom.cfg')
            content: File content to write
            pin: Admin PIN to authorize write operation

        WARNING: Be careful writing to printer.cfg - invalid config can prevent Klipper from starting.
        """
        if pin != config.ADMIN_PIN:
            return json.dumps({"error": "Invalid PIN. Write operation not authorized."})

        client = get_client()
        session = await client._get_session()

        # Determine root
        if filepath.startswith("config/"):
            root = "config"
            filename = filepath[7:]
        else:
            root = "config"
            filename = filepath

        url = f"{client.base_url}/server/files/upload"

        try:
            # Create multipart form data
            import aiohttp

            data = aiohttp.FormData()
            data.add_field(
                "file",
                content.encode("utf-8"),
                filename=filename,
                content_type="text/plain",
            )
            data.add_field("root", root)

            async with session.post(url, data=data) as response:
                response.raise_for_status()
                result = await response.json()

                return json.dumps(
                    {
                        "success": True,
                        "filepath": f"{root}/{filename}",
                        "message": "File written successfully",
                    }
                )
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(write=True)
    async def delete_file(filepath: str, pin: str) -> str:
        """
        Delete a file from the printer.
        REQUIRES: Admin PIN for safety.

        Args:
            filepath: Path to file (e.g., 'gcodes/old_print.gcode')
            pin: Admin PIN to authorize deletion
        """
        if pin != config.ADMIN_PIN:
            return json.dumps(
                {"error": "Invalid PIN. Delete operation not authorized."}
            )

        client = get_client()

        result = await client.delete_file(filepath)

        if "error" in result:
            return json.dumps({"error": result["error"]})

        return json.dumps({"success": True, "deleted": filepath})

    @mcp.tool()
    async def get_gcode_metadata(filename: str) -> str:
        """
        Get metadata for a G-code file (estimated time, filament, thumbnails, etc).

        Args:
            filename: G-code filename
        """
        client = get_client()
        result = await client.get_file_metadata(filename)

        if "error" in result:
            return json.dumps({"error": result["error"]})

        metadata = result.get("result", {})

        # Format useful info
        formatted = {
            "filename": metadata.get("filename"),
            "size_mb": round(metadata.get("size", 0) / 1024 / 1024, 2),
            "modified": metadata.get("modified"),
            "slicer": metadata.get("slicer"),
            "slicer_version": metadata.get("slicer_version"),
            "estimated_time": metadata.get("estimated_time"),
            "estimated_time_formatted": format_duration(
                metadata.get("estimated_time"), empty="unknown"
            ),
            "filament_total_mm": metadata.get("filament_total"),
            "filament_total_grams": metadata.get("filament_weight_total"),
            "layer_height": metadata.get("layer_height"),
            "first_layer_height": metadata.get("first_layer_height"),
            "object_height": metadata.get("object_height"),
            "first_layer_bed_temp": metadata.get("first_layer_bed_temp"),
            "first_layer_extr_temp": metadata.get("first_layer_extr_temp"),
            "nozzle_diameter": metadata.get("nozzle_diameter"),
            "has_thumbnails": len(metadata.get("thumbnails", [])) > 0,
        }

        return json.dumps(formatted, indent=2)

    @mcp.tool()
    async def list_config_files() -> str:
        """List all configuration files (*.cfg) in the config directory."""
        client = get_client()
        result = await client.get_directory("config")

        if "error" in result:
            return json.dumps({"error": result["error"]})

        data = result.get("result", {})

        config_files = []
        for item in data.get("files", []):
            filename = item.get("filename", "")
            if filename.endswith(".cfg"):
                config_files.append(
                    {
                        "name": filename,
                        "size": item.get("size"),
                        "modified": item.get("modified"),
                    }
                )

        return json.dumps({"config_files": config_files}, indent=2)

    @mcp.tool()
    async def search_in_file(filepath: str, search_term: str) -> str:
        """
        Search for a term in a file and return matching lines.

        Args:
            filepath: Path to file (e.g., 'config/printer.cfg')
            search_term: Text to search for (case-insensitive)
        """
        # First read the file
        client = get_client()

        if filepath.startswith("config/"):
            root = "config"
            filename = filepath[7:]
        elif filepath.startswith("logs/"):
            root = "logs"
            filename = filepath[5:]
        else:
            root = "config"
            filename = filepath

        session = await client._get_session()
        url = f"{client.base_url}/server/files/{root}/{filename}"

        try:
            async with session.get(url) as response:
                if response.status == 404:
                    return json.dumps({"error": f"File not found: {filepath}"})
                response.raise_for_status()
                content = await response.text()

                matches = []
                search_lower = search_term.lower()

                for i, line in enumerate(content.split("\n"), 1):
                    if search_lower in line.lower():
                        matches.append({"line_number": i, "content": line.strip()})

                return json.dumps(
                    {
                        "filepath": filepath,
                        "search_term": search_term,
                        "matches": matches,
                        "match_count": len(matches),
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)})
