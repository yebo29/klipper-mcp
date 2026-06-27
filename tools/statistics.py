"""
Print Statistics Tools
Print history, totals, and analytics
"""

import json
from typing import Optional
import config
from moonraker import get_client


def register_statistics_tools(mcp):
    """Register print statistics tools."""

    @mcp.tool()
    async def get_print_history(
        limit: int = 20, status_filter: Optional[str] = None
    ) -> str:
        """
        Get print job history.

        Args:
            limit: Number of jobs to return (default: 20, max: 100)
            status_filter: Filter by status - 'completed', 'cancelled', 'error' (optional)
        """
        limit = min(limit, 100)

        client = get_client()
        result = await client.get_print_history(limit=limit)

        if "error" in result:
            return json.dumps({"error": result["error"]})

        data = result.get("result", {})
        jobs = data.get("jobs", [])

        formatted_jobs = []
        for job in jobs:
            # Apply status filter if specified
            job_status = job.get("status", "")
            if status_filter and job_status != status_filter:
                continue

            formatted_jobs.append(
                {
                    "id": job.get("job_id"),
                    "filename": job.get("filename"),
                    "status": job_status,
                    "start_time": job.get("start_time"),
                    "end_time": job.get("end_time"),
                    "print_duration": format_duration(job.get("print_duration")),
                    "total_duration": format_duration(job.get("total_duration")),
                    "filament_used_mm": round(job.get("filament_used", 0), 1),
                    "filament_used_g": round(
                        job.get("filament_used", 0) * 0.00125, 2
                    ),  # Approximate
                }
            )

        return json.dumps(
            {
                "total_count": data.get("count", 0),
                "returned": len(formatted_jobs),
                "jobs": formatted_jobs,
            },
            indent=2,
        )

    @mcp.tool()
    async def get_print_totals() -> str:
        """
        Get cumulative print statistics totals.
        Includes total print time, filament used, and job counts.
        """
        client = get_client()
        result = await client.get_print_totals()

        if "error" in result:
            return json.dumps({"error": result["error"]})

        data = result.get("result", {}).get("job_totals", {})

        totals = {
            "total_jobs": data.get("total_jobs", 0),
            "total_time": {
                "seconds": data.get("total_time", 0),
                "formatted": format_duration(data.get("total_time", 0)),
            },
            "total_print_time": {
                "seconds": data.get("total_print_time", 0),
                "formatted": format_duration(data.get("total_print_time", 0)),
            },
            "total_filament_used": {
                "mm": round(data.get("total_filament_used", 0), 1),
                "meters": round(data.get("total_filament_used", 0) / 1000, 2),
                "grams_approx": round(
                    data.get("total_filament_used", 0) * 0.00125, 1
                ),  # Approximate
            },
            "longest_job": {
                "seconds": data.get("longest_job", 0),
                "formatted": format_duration(data.get("longest_job", 0)),
            },
            "longest_print": {
                "seconds": data.get("longest_print", 0),
                "formatted": format_duration(data.get("longest_print", 0)),
            },
        }

        return json.dumps(totals, indent=2)

    @mcp.tool()
    async def get_job_details(job_id: str) -> str:
        """
        Get detailed information about a specific print job.

        Args:
            job_id: The job ID from print history
        """
        client = get_client()
        result = await client.get_job_details(job_id)

        if "error" in result:
            return json.dumps({"error": result["error"]})

        job = result.get("result", {}).get("job", {})

        return json.dumps(
            {
                "id": job.get("job_id"),
                "filename": job.get("filename"),
                "status": job.get("status"),
                "start_time": job.get("start_time"),
                "end_time": job.get("end_time"),
                "print_duration": format_duration(job.get("print_duration")),
                "total_duration": format_duration(job.get("total_duration")),
                "filament_used_mm": round(job.get("filament_used", 0), 1),
                "metadata": job.get("metadata", {}),
                "auxiliary_data": job.get("auxiliary_data", []),
            },
            indent=2,
        )

    @mcp.tool()
    async def get_filament_usage_summary() -> str:
        """
        Get summary of filament usage across all prints.
        Useful for tracking material consumption.
        """
        client = get_client()

        # Get last 100 jobs for analysis
        result = await client.get_print_history(limit=100)

        if "error" in result:
            return json.dumps({"error": result["error"]})

        jobs = result.get("result", {}).get("jobs", [])

        # Analyze by status
        completed_filament = 0
        cancelled_filament = 0
        total_filament = 0
        completed_count = 0
        cancelled_count = 0

        for job in jobs:
            filament = job.get("filament_used", 0)
            total_filament += filament

            if job.get("status") == "completed":
                completed_filament += filament
                completed_count += 1
            elif job.get("status") == "cancelled":
                cancelled_filament += filament
                cancelled_count += 1

        # Calculate waste percentage
        waste_percent = (
            (cancelled_filament / total_filament * 100) if total_filament > 0 else 0
        )

        return json.dumps(
            {
                "analysis_period": f"Last {len(jobs)} jobs",
                "total_filament": {
                    "mm": round(total_filament, 1),
                    "meters": round(total_filament / 1000, 2),
                    "grams_approx": round(total_filament * 0.00125, 1),
                },
                "completed_prints": {
                    "count": completed_count,
                    "filament_mm": round(completed_filament, 1),
                },
                "cancelled_prints": {
                    "count": cancelled_count,
                    "filament_mm": round(cancelled_filament, 1),
                },
                "waste_percentage": round(waste_percent, 1),
                "success_rate": (
                    round(completed_count / len(jobs) * 100, 1) if jobs else 0
                ),
            },
            indent=2,
        )

    @mcp.tool()
    async def get_recent_prints(hours: int = 24) -> str:
        """
        Get prints from the last N hours.

        Args:
            hours: Number of hours to look back (default: 24)
        """
        import time

        client = get_client()
        result = await client.get_print_history(limit=50)

        if "error" in result:
            return json.dumps({"error": result["error"]})

        jobs = result.get("result", {}).get("jobs", [])

        cutoff_time = time.time() - (hours * 3600)

        recent_jobs = []
        for job in jobs:
            start_time = job.get("start_time", 0)
            if start_time >= cutoff_time:
                recent_jobs.append(
                    {
                        "filename": job.get("filename"),
                        "status": job.get("status"),
                        "print_duration": format_duration(job.get("print_duration")),
                        "start_time": job.get("start_time"),
                    }
                )

        return json.dumps(
            {
                "period": f"Last {hours} hours",
                "count": len(recent_jobs),
                "jobs": recent_jobs,
            },
            indent=2,
        )

    @mcp.tool()
    async def get_average_print_stats() -> str:
        """
        Calculate average print statistics from job history.
        """
        client = get_client()
        result = await client.get_print_history(limit=50)

        if "error" in result:
            return json.dumps({"error": result["error"]})

        jobs = result.get("result", {}).get("jobs", [])

        # Filter completed jobs only
        completed = [j for j in jobs if j.get("status") == "completed"]

        if not completed:
            return json.dumps({"message": "No completed prints to analyze"})

        # Calculate averages
        total_duration = sum(j.get("print_duration", 0) for j in completed)
        total_filament = sum(j.get("filament_used", 0) for j in completed)

        avg_duration = total_duration / len(completed)
        avg_filament = total_filament / len(completed)

        return json.dumps(
            {
                "sample_size": len(completed),
                "average_print_duration": {
                    "seconds": round(avg_duration),
                    "formatted": format_duration(avg_duration),
                },
                "average_filament_per_print": {
                    "mm": round(avg_filament, 1),
                    "grams_approx": round(avg_filament * 0.00125, 2),
                },
                "total_analyzed": len(jobs),
                "completed_count": len(completed),
            },
            indent=2,
        )


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if not seconds:
        return "0m"

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"
