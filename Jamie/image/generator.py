"""
Jamie Image Generator — Uses Pollinations.ai (free, no API key needed)
"""

import aiohttp
import logging
import urllib.parse
import io
import os

log = logging.getLogger("jamie.image")

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"


class ImageGenerator:
    """Generate images via Pollinations.ai free API."""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120)
        )

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def generate(self, prompt: str, width: int = 1024, height: int = 1024) -> bytes | None:
        """Generate an image from a text prompt. Returns PNG bytes or None."""
        if not self.session:
            await self.start()

        encoded = urllib.parse.quote(prompt)
        url = f"{POLLINATIONS_BASE}/{encoded}?width={width}&height={height}&nologo=true&model=flux"

        log.info("Generating image: %s", prompt[:80])
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    if len(data) > 1000:  # sanity check — real images are > 1KB
                        log.info("Image generated: %d bytes", len(data))
                        return data
                    log.warning("Image too small (%d bytes), likely an error", len(data))
                else:
                    error = await resp.text()
                    log.error("Image generation failed %d: %s", resp.status, error[:200])
        except aiohttp.ClientError as e:
            log.error("Image request failed: %s", e)

        return None
