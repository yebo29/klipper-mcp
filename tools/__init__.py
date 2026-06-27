"""
MCP Tools for Klipper/Moonraker
"""

from .printer import register_printer_tools
from .toolchanger import register_toolchanger_tools
from .led_effects import register_led_tools
from .filesystem import register_filesystem_tools
from .camera import register_camera_tools
from .statistics import register_statistics_tools
from .diagnostics import register_diagnostics_tools
from .temperature import register_temperature_tools
from .spoolman import register_spoolman_tools
from .notifications import register_notification_tools
from .backup import register_backup_tools
from .gcode_analysis import register_gcode_analysis_tools
from .system import register_system_tools
from .tmc import register_tmc_tools


def register_all_tools(mcp):
    """Register all tool modules with the MCP server."""
    register_printer_tools(mcp)
    register_toolchanger_tools(mcp)
    register_led_tools(mcp)
    register_filesystem_tools(mcp)
    register_camera_tools(mcp)
    register_statistics_tools(mcp)
    register_diagnostics_tools(mcp)
    register_temperature_tools(mcp)
    register_spoolman_tools(mcp)
    register_notification_tools(mcp)
    register_backup_tools(mcp)
    register_gcode_analysis_tools(mcp)
    register_system_tools(mcp)
    register_tmc_tools(mcp)
