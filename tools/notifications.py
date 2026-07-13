"""
Notification Tools
Alerts, webhooks, and text-to-speech announcements
"""

import json
import aiohttp
import config


def register_notification_tools(mcp):
    """Register notification tools."""

    async def send_webhook(url: str, payload: dict) -> dict:
        """Send webhook notification."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    return {"success": response.status < 400, "status": response.status}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool(write=True)
    async def send_notification(title: str, message: str, level: str = "info") -> str:
        """
        Send a notification via configured channels.

        Args:
            title: Notification title
            message: Notification message body
            level: Severity level - 'info', 'warning', 'error', 'success'
        """
        results = {}

        # Discord webhook
        if config.DISCORD_WEBHOOK_URL:
            color_map = {
                "info": 3447003,
                "warning": 16776960,
                "error": 15158332,
                "success": 3066993,
            }
            discord_payload = {
                "embeds": [
                    {
                        "title": f"🖨️ {title}",
                        "description": message,
                        "color": color_map.get(level, 3447003),
                        "footer": {"text": f"Printer: {config.PRINTER_NAME}"},
                    }
                ]
            }
            results["discord"] = await send_webhook(
                config.DISCORD_WEBHOOK_URL, discord_payload
            )

        # Slack webhook
        if config.SLACK_WEBHOOK_URL:
            emoji_map = {"info": "ℹ️", "warning": "⚠️", "error": "🚨", "success": "✅"}
            slack_payload = {
                "text": f"{emoji_map.get(level, 'ℹ️')} *{title}*\n{message}\n_Printer: {config.PRINTER_NAME}_"
            }
            results["slack"] = await send_webhook(
                config.SLACK_WEBHOOK_URL, slack_payload
            )

        # Pushover
        if config.PUSHOVER_USER_KEY and config.PUSHOVER_API_TOKEN:
            priority_map = {"info": 0, "warning": 0, "error": 1, "success": 0}
            pushover_payload = {
                "token": config.PUSHOVER_API_TOKEN,
                "user": config.PUSHOVER_USER_KEY,
                "title": title,
                "message": message,
                "priority": priority_map.get(level, 0),
            }
            results["pushover"] = await send_webhook(
                "https://api.pushover.net/1/messages.json", pushover_payload
            )

        # Moonraker notification (shows in UI)
        from moonraker import get_client

        client = get_client()
        await client.run_gcode(
            f'RESPOND PREFIX="{level.upper()}" MSG="{title}: {message}"'
        )
        results["moonraker"] = {"success": True}

        return json.dumps({"notification_sent": True, "channels": results}, indent=2)

    @mcp.tool(write=True)
    async def announce_tts(message: str) -> str:
        """
        Make a text-to-speech announcement through the printer's speaker.
        Requires pyttsx3 and audio output on the CB1.

        Args:
            message: The message to speak
        """
        if not config.TTS_ENABLED:
            return json.dumps(
                {"error": "TTS not enabled", "hint": "Set TTS_ENABLED=true in config"}
            )

        try:
            # Note: This runs synchronously - for production, consider async TTS
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", config.TTS_RATE)
            engine.setProperty("volume", config.TTS_VOLUME)
            engine.say(message)
            engine.runAndWait()

            return json.dumps({"success": True, "message_spoken": message})
        except ImportError:
            return json.dumps(
                {"error": "pyttsx3 not installed", "hint": "Run: pip install pyttsx3"}
            )
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(write=True)
    async def notify_print_complete(
        filename: str, print_time: str, success: bool = True
    ) -> str:
        """
        Send a print completion notification.

        Args:
            filename: Name of the printed file
            print_time: Duration of the print
            success: Whether print completed successfully
        """
        if success:
            title = "Print Complete ✅"
            message = f"'{filename}' finished successfully!\nPrint time: {print_time}"
            level = "success"
        else:
            title = "Print Failed ❌"
            message = f"'{filename}' failed.\nTime elapsed: {print_time}"
            level = "error"

        # Use the generic notification system
        notification_result = await send_notification(title, message, level)

        # Also do TTS announcement if enabled
        if config.TTS_ENABLED:
            tts_message = f"Print {'complete' if success else 'failed'}. {filename}"
            try:
                import pyttsx3

                engine = pyttsx3.init()
                engine.setProperty("rate", config.TTS_RATE)
                engine.say(tts_message)
                engine.runAndWait()
            except Exception:
                pass  # TTS failure shouldn't fail the notification

        return notification_result

    @mcp.tool(write=True)
    async def notify_temperature_alert(
        heater: str, current_temp: float, expected_temp: float, alert_type: str
    ) -> str:
        """
        Send a temperature alert notification.

        Args:
            heater: Heater name (extruder, heater_bed)
            current_temp: Current temperature
            expected_temp: Expected/target temperature
            alert_type: Type of alert (overtemp, undertemp, thermal_runaway)
        """
        alert_messages = {
            "overtemp": f"🔥 {heater} overheating! {current_temp}°C (target: {expected_temp}°C)",
            "undertemp": f"❄️ {heater} too cold! {current_temp}°C (target: {expected_temp}°C)",
            "thermal_runaway": f"🚨 THERMAL RUNAWAY DETECTED on {heater}! Printer may need emergency stop!",
        }

        message = alert_messages.get(
            alert_type, f"Temperature alert on {heater}: {current_temp}°C"
        )

        level = "error" if alert_type == "thermal_runaway" else "warning"

        return await send_notification(
            f"Temperature Alert - {config.PRINTER_NAME}", message, level
        )

    @mcp.tool()
    async def get_notification_config() -> str:
        """Get current notification configuration."""
        return json.dumps(
            {
                "discord": {
                    "enabled": bool(config.DISCORD_WEBHOOK_URL),
                    "configured": "webhook_url" if config.DISCORD_WEBHOOK_URL else None,
                },
                "slack": {
                    "enabled": bool(config.SLACK_WEBHOOK_URL),
                    "configured": "webhook_url" if config.SLACK_WEBHOOK_URL else None,
                },
                "pushover": {
                    "enabled": bool(
                        config.PUSHOVER_USER_KEY and config.PUSHOVER_API_TOKEN
                    ),
                    "configured": (
                        "user_key + api_token" if config.PUSHOVER_USER_KEY else None
                    ),
                },
                "tts": {
                    "enabled": config.TTS_ENABLED,
                    "rate": config.TTS_RATE,
                    "volume": config.TTS_VOLUME,
                },
                "moonraker": {
                    "enabled": True,
                    "note": "Always sends RESPOND commands to Moonraker UI",
                },
            },
            indent=2,
        )

    @mcp.tool(write=True)
    async def test_notifications() -> str:
        """
        Send a test notification to all configured channels.
        Useful for verifying notification setup.
        """
        return await send_notification(
            "Test Notification",
            "This is a test notification from Klipper MCP server. If you received this, notifications are working!",
            "info",
        )

    @mcp.tool(write=True)
    async def console_message(message: str, prefix: str = "info") -> str:
        """
        Send a message to the Moonraker/Mainsail/Fluidd console.

        Args:
            message: The message to display
            prefix: Prefix type - 'info', 'warning', 'error', or custom
        """
        from moonraker import get_client

        client = get_client()

        # RESPOND with prefix shows in console
        gcode = f'RESPOND PREFIX="{prefix.upper()}" MSG="{message}"'
        result = await client.run_gcode(gcode)

        if "error" in result:
            return json.dumps({"error": result["error"]})

        return json.dumps(
            {"success": True, "console_message": f"[{prefix.upper()}] {message}"}
        )
