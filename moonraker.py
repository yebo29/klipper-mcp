"""
Async Moonraker API Client
Handles all communication with Moonraker's HTTP API.
"""

import aiohttp
import asyncio
from typing import Any, Optional, Dict, List
import config


class MoonrakerClient:
    """Async client for Moonraker HTTP API."""

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or config.MOONRAKER_URL).rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        json_data: Dict = None,
        data: Any = None,
    ) -> Dict:
        """Make HTTP request to Moonraker."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with session.request(
                method, url, params=params, json=json_data, data=data
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            return {"error": str(e)}

    async def get(self, endpoint: str, params: Dict = None) -> Dict:
        """HTTP GET request."""
        return await self._request("GET", endpoint, params=params)

    async def post(
        self, endpoint: str, json_data: Dict = None, data: Any = None
    ) -> Dict:
        """HTTP POST request."""
        return await self._request("POST", endpoint, json_data=json_data, data=data)

    async def delete(self, endpoint: str, params: Dict = None) -> Dict:
        """HTTP DELETE request."""
        return await self._request("DELETE", endpoint, params=params)

    # =========================================================================
    # PRINTER STATUS
    # =========================================================================

    async def get_printer_info(self) -> Dict:
        """Get general printer info."""
        return await self.get("/printer/info")

    async def get_server_info(self) -> Dict:
        """Get Moonraker server info."""
        return await self.get("/server/info")

    async def query_printer_objects(self, objects: Dict[str, List[str]]) -> Dict:
        """Query printer objects for specific attributes."""
        return await self.post("/printer/objects/query", json_data={"objects": objects})

    async def get_printer_status(self) -> Dict:
        """Get comprehensive printer status."""
        objects = {
            "heater_bed": ["temperature", "target", "power"],
            "extruder": ["temperature", "target", "power", "pressure_advance"],
            "toolhead": [
                "position",
                "homed_axes",
                "print_time",
                "estimated_print_time",
            ],
            "print_stats": [
                "state",
                "filename",
                "total_duration",
                "print_duration",
                "filament_used",
                "message",
            ],
            "virtual_sdcard": ["file_position", "progress", "is_active"],
            "gcode_move": ["speed", "speed_factor", "extrude_factor"],
            "fan": ["speed"],
            "idle_timeout": ["state", "printing_time"],
        }
        return await self.query_printer_objects(objects)

    # =========================================================================
    # G-CODE EXECUTION
    # =========================================================================

    async def run_gcode(self, script: str) -> Dict:
        """Execute G-code script."""
        return await self.post("/printer/gcode/script", json_data={"script": script})

    async def emergency_stop(self) -> Dict:
        """Trigger emergency stop."""
        return await self.post("/printer/emergency_stop")

    async def restart_firmware(self) -> Dict:
        """Restart firmware (FIRMWARE_RESTART)."""
        return await self.post("/printer/firmware_restart")

    async def restart_host(self) -> Dict:
        """Restart Klipper host."""
        return await self.post("/printer/restart")

    # =========================================================================
    # TEMPERATURE
    # =========================================================================

    async def get_temperature_store(self) -> Dict:
        """Get cached temperature history."""
        return await self.get("/server/temperature_store")

    async def set_heater_temperature(self, heater: str, target: float) -> Dict:
        """Set heater target temperature."""
        if heater == "extruder":
            gcode = f"M104 S{target}"
        elif heater == "heater_bed":
            gcode = f"M140 S{target}"
        else:
            gcode = f"SET_HEATER_TEMPERATURE HEATER={heater} TARGET={target}"
        return await self.run_gcode(gcode)

    # =========================================================================
    # FILE MANAGEMENT
    # =========================================================================

    async def list_files(self, root: str = "gcodes") -> Dict:
        """List files in a directory."""
        return await self.get("/server/files/list", params={"root": root})

    async def get_file_metadata(self, filename: str) -> Dict:
        """Get metadata for a G-code file."""
        return await self.get("/server/files/metadata", params={"filename": filename})

    async def delete_file(self, path: str) -> Dict:
        """Delete a file."""
        return await self.delete(f"/server/files/{path}")

    async def get_directory(self, path: str = "gcodes") -> Dict:
        """Get directory listing with details."""
        return await self.get("/server/files/directory", params={"path": path})

    # =========================================================================
    # PRINT CONTROL
    # =========================================================================

    async def start_print(self, filename: str) -> Dict:
        """Start printing a file."""
        return await self.post("/printer/print/start", json_data={"filename": filename})

    async def pause_print(self) -> Dict:
        """Pause current print."""
        return await self.post("/printer/print/pause")

    async def resume_print(self) -> Dict:
        """Resume paused print."""
        return await self.post("/printer/print/resume")

    async def cancel_print(self) -> Dict:
        """Cancel current print."""
        return await self.post("/printer/print/cancel")

    # =========================================================================
    # PRINT HISTORY
    # =========================================================================

    async def get_print_history(self, limit: int = 50, start: int = 0) -> Dict:
        """Get print job history."""
        return await self.get(
            "/server/history/list", params={"limit": limit, "start": start}
        )

    async def get_print_totals(self) -> Dict:
        """Get print statistics totals."""
        return await self.get("/server/history/totals")

    async def get_job_details(self, job_id: str) -> Dict:
        """Get details for a specific job."""
        return await self.get("/server/history/job", params={"uid": job_id})

    # =========================================================================
    # BED MESH
    # =========================================================================

    async def get_bed_mesh(self) -> Dict:
        """Get current bed mesh data."""
        objects = {
            "bed_mesh": [
                "profile_name",
                "mesh_min",
                "mesh_max",
                "probed_matrix",
                "profiles",
            ]
        }
        return await self.query_printer_objects(objects)

    async def load_bed_mesh(self, profile: str) -> Dict:
        """Load a bed mesh profile."""
        return await self.run_gcode(f"BED_MESH_PROFILE LOAD={profile}")

    # =========================================================================
    # WEBCAM
    # =========================================================================

    async def get_webcam_list(self) -> Dict:
        """Get list of configured webcams."""
        return await self.get("/server/webcams/list")

    async def get_webcam_snapshot(self, webcam_name: str = None) -> bytes:
        """Get webcam snapshot as bytes."""
        session = await self._get_session()
        url = config.CAMERA_SNAPSHOT_URL

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()
        except aiohttp.ClientError as e:
            return None

    # =========================================================================
    # TIMELAPSE (moonraker-timelapse plugin)
    # =========================================================================

    async def get_timelapse_settings(self) -> Dict:
        """Get timelapse settings."""
        return await self.get("/machine/timelapse/settings")

    async def set_timelapse_settings(self, settings: Dict) -> Dict:
        """Update timelapse settings."""
        return await self.post("/machine/timelapse/settings", json_data=settings)

    async def render_timelapse(self) -> Dict:
        """Render current timelapse."""
        return await self.post("/machine/timelapse/render")

    async def list_timelapses(self) -> Dict:
        """List rendered timelapses."""
        return await self.get("/server/files/list", params={"root": "timelapse"})

    # =========================================================================
    # ANNOUNCEMENTS / LOGS
    # =========================================================================

    async def get_gcode_store(self, count: int = 100) -> Dict:
        """Get recent G-code responses."""
        return await self.get("/server/gcode_store", params={"count": count})

    # =========================================================================
    # MACHINE CONTROL
    # =========================================================================

    async def reboot_system(self) -> Dict:
        """Reboot the host system."""
        return await self.post("/machine/reboot")

    async def shutdown_system(self) -> Dict:
        """Shutdown the host system."""
        return await self.post("/machine/shutdown")


# Singleton instance
_client: Optional[MoonrakerClient] = None


def init_client() -> MoonrakerClient:
    """Initialize the Moonraker client singleton."""
    global _client
    if _client is None:
        _client = MoonrakerClient()
    return _client


def get_client() -> MoonrakerClient:
    """Get or create Moonraker client instance."""
    global _client
    if _client is None:
        _client = MoonrakerClient()
    return _client


async def close_client():
    """Close the Moonraker client connection."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
