import asyncio
import traceback

import discord
import discord.http
import uvicorn

from reo.engine.bot import AutoShardedBot
from reo.console.logging import logger
from reo.config.config import BotConfigClass

BetConfig = BotConfigClass()
bot = AutoShardedBot()

# Seedhe module se app ko nikal liya, ab kabhi "not defined" nahi aayega
from reo.surface.server import app

async def main():
    try:
        from reo.workflows.bootstrap import prepare_runtime
        from reo.surface import server as surface_server
        from reo.style.sync_emojis import run_sync

        await prepare_runtime()
        surface_server.bind_bot(bot)
        logger.separator()

        # Fast Emoji Synchronization
        if BetConfig.SYNC_EMOJIS:
            run_sync()
        else:
            logger.info("EmojiSync is currently disabled via config.")
        logger.separator()

        await bot.load_extension("reo.src")

        tasks = []

        async def start_bot():
            try:
                await bot.start(BetConfig.TOKEN, reconnect=True)
            except KeyboardInterrupt:
                logger.error("Bot has been stopped")
            except discord.RateLimited as error:
                logger.error(f"You are rate limited. Retrying in {error.retry_after}s")
            except discord.LoginFailure as error:
                logger.error(f"Login failed: {error}")
            except discord.HTTPException as error:
                retry_after = error.response.headers.get('Retry-After')
                logger.error(f"You are rate limited. Retrying in {retry_after if retry_after else 'N/A'}s")
                if retry_after == "N/A":
                    return
                logger.error(f"Rate Limit details: {error.response.status}")
                logger.error(f"Response headers: {error.response.headers}")
                logger.error(f"Response text: {error.status} {error.text}")
                await asyncio.sleep(int(retry_after))

        async def start_web():
            try:
                import logging
                class EndpointFilter(logging.Filter):
                    def filter(self, record: logging.LogRecord) -> bool:
                        return "/live" not in record.getMessage()

                logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

                web_config = uvicorn.Config(
                    app,
                    host=BetConfig.WEB_HOST,
                    port=BetConfig.WEB_PORT,
                )
                server = uvicorn.Server(web_config)
                await server.serve()
            except Exception:
                logger.error(f"Error in file {__file__}: {traceback.format_exc()}")

        if BetConfig.DASHBOARD_ENABLED:
            try:
                tasks.append(asyncio.create_task(start_web()))
            except Exception:
                logger.error(f"Error in file {__file__}: {traceback.format_exc()}")
        else:
            logger.info("V023||3isDashboard is disabled via config.\\000")
            
        try:
            tasks.append(asyncio.create_task(start_bot()))
        except Exception:
            logger.error(f"Error in file {__file__}: {traceback.format_exc()}")

        await asyncio.gather(*tasks)

    except Exception:
        logger.error(f"Error in file {__file__}: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())
    
