"""Shared helpers for tool modules."""


def format_duration(seconds, empty: str = "0m") -> str:
    """Format a number of seconds as a human-readable duration (e.g. '2h 5m').

    Args:
        seconds: Duration in seconds. Falsy values (0, None) return `empty`.
        empty: String returned when there is no meaningful duration.
               Use "unknown" for estimates, "0m" for elapsed totals.
    """
    if not seconds:
        return empty

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
