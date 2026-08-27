"""Asynchronous lightweight Health-Check web server for Render / UptimeRobot."""

from aiohttp import web

from src.core.logger import get_logger

logger = get_logger(__name__)


async def _handle_health_check(request: web.Request) -> web.Response:
    """Handle GET and HEAD health checks."""
    return web.Response(
        text="OK",
        content_type="text/plain",
        charset="utf-8",
        status=200,
        headers={"Content-Length": "2"},
    )


def create_health_app() -> web.Application:
    """Create configured aiohttp web application for health monitoring."""
    app = web.Application()
    app.router.add_get("/", _handle_health_check)
    app.router.add_get("/health", _handle_health_check)
    return app


async def start_health_server(port: int = 10000, host: str = "0.0.0.0") -> web.AppRunner:
    """Start the asynchronous health check web server."""
    app = create_health_app()
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"🌐 Health-Check Web Server listening on http://{host}:{port}")
    return runner


async def stop_health_server(runner: web.AppRunner | None) -> None:
    """Gracefully cleanup and stop the health check web server."""
    if runner:
        logger.info("Stopping Health-Check Web Server...")
        await runner.cleanup()
