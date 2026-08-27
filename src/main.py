"""Application entrypoint coordinating bot polling, analytics buffer, and health server lifecycle."""

import asyncio
import sys

from aiohttp import web
from telegram import Update
from telegram.error import Conflict, NetworkError

from src.bot.app import create_bot_application
from src.core.config import get_settings
from src.core.logger import get_logger, setup_logging
from src.infrastructure.web.health import start_health_server, stop_health_server
from src.services.analytics_buffer import get_analytics_buffer
from src.services.http_client import close_http_session

logger = get_logger(__name__)


async def run_bot_polling() -> None:
    """Execute bot polling, analytics buffer, and health check server in unified asyncio loop."""
    settings = get_settings()
    health_runner: web.AppRunner | None = None
    analytics_buffer = get_analytics_buffer()

    try:
        health_runner = await start_health_server(port=settings.PORT)
        analytics_buffer.start(interval_seconds=30.0)

        while True:
            application = None
            try:
                application = create_bot_application()
                await application.initialize()
                await application.start()

                logger.info("🚀 BugaichyBot Vanilla Edition running in polling mode...")
                if application.updater:
                    await application.updater.start_polling(
                        allowed_updates=Update.ALL_TYPES,
                        drop_pending_updates=True,
                        bootstrap_retries=-1,
                        timeout=30,
                    )

                    # Keep running until cancelled
                    while application.updater and application.updater.running:
                        await asyncio.sleep(1)

                await application.stop()
                await application.shutdown()
                break

            except Conflict as e:
                logger.warning(
                    f"⚠️ Telegram 409 Conflict (previous container is still terminating): {e}. Retrying in 10s..."
                )
                if application:
                    try:
                        await application.shutdown()
                    except Exception:
                        pass
                await asyncio.sleep(10)
            except NetworkError as e:
                logger.warning(f"⚠️ Network error: {e}. Retrying in 5s...")
                if application:
                    try:
                        await application.shutdown()
                    except Exception:
                        pass
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(
                    f"❌ Unexpected error in bot loop: {e}. Retrying in 10s...", exc_info=True
                )
                if application:
                    try:
                        await application.shutdown()
                    except Exception:
                        pass
                await asyncio.sleep(10)

    except asyncio.CancelledError:
        logger.info("Received cancellation signal. Initiating graceful shutdown...")
    finally:
        # Graceful cleanup in reverse order
        logger.info("Initiating resource teardown...")
        await analytics_buffer.stop()
        if health_runner:
            await stop_health_server(health_runner)
        await close_http_session()
        logger.info("Graceful shutdown completed.")


def main() -> None:
    """Sync entrypoint initializing logging and starting asyncio runner."""
    setup_logging()
    logger.info("Initializing BugaichyBot application...")

    try:
        asyncio.run(run_bot_polling())
    except KeyboardInterrupt:
        logger.info("Application stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Fatal error during execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
