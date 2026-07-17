"""
ImageCog — /generate command for image creation.
Uses LLM to enhance prompts, then Pollinations.ai to generate.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import io

log = logging.getLogger("jamie.image")


class ImageCog(commands.Cog):
    """Image generation commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="generate",
        description="Generate an image from a text description"
    )
    @app_commands.describe(
        prompt="What you want the image to look like",
        private="Only show the result to you (default: false)"
    )
    async def generate(self, interaction: discord.Interaction, prompt: str,
                       private: bool = False):
        """Generate an image from a text prompt."""
        db = self.bot.db

        if not await db.is_setup(interaction.guild_id):
            await interaction.response.send_message(
                "❌ I'm not set up yet. An admin needs to run `/setup` first.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True, ephemeral=private)

        # Use LLM to enhance the prompt
        enhanced_prompt = await self.bot.llm.generate_image_prompt(prompt)
        log.info("Image prompt: '%s' → '%s'", prompt[:60], enhanced_prompt[:60])

        # Generate the image
        image_bytes = await self.bot.image_gen.generate(enhanced_prompt)

        if not image_bytes:
            await interaction.followup.send(
                "❌ Couldn't generate that image. Try a different prompt.",
                ephemeral=private,
            )
            return

        # Send the image
        file = discord.File(
            fp=io.BytesIO(image_bytes),
            filename="jamie_gen.png",
            description=prompt,
        )

        embed = discord.Embed(
            title="🎨 Image Generated",
            description=f"**Prompt:** {prompt}\n**Enhanced:** {enhanced_prompt[:200]}",
            color=0xD98AFF,
        )
        embed.set_image(url="attachment://jamie_gen.png")
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed, file=file, ephemeral=private)

    @app_commands.command(
        name="imagine",
        description="Let Jamie imagine and generate something wild"
    )
    async def imagine(self, interaction: discord.Interaction):
        """Jamie generates a random creative image."""
        db = self.bot.db

        if not await db.is_setup(interaction.guild_id):
            await interaction.response.send_message(
                "❌ I'm not set up yet. An admin needs to run `/setup` first.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        # Let Jamie come up with something
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Jamie — come up with a vivid, creative image prompt. "
                    "Make it something wild, dark, or metal-inspired. "
                    "Output ONLY the image prompt, nothing else."
                ),
            },
            {"role": "user", "content": "Imagine something and describe it as an image prompt."},
        ]

        prompt = await self.bot.llm.chat(messages, temperature=1.0, max_tokens=150)
        prompt = prompt.strip().strip('"\'')

        image_bytes = await self.bot.image_gen.generate(prompt)

        if not image_bytes:
            await interaction.followup.send("❌ Couldn't generate the image. Try again.")
            return

        file = discord.File(
            fp=io.BytesIO(image_bytes),
            filename="jamie_imagine.png",
            description=prompt,
        )

        embed = discord.Embed(
            title="🔥 Jamie's Imagination",
            description=f"**What I imagined:** {prompt[:300]}",
            color=0xD98AFF,
        )
        embed.set_image(url="attachment://jamie_imagine.png")

        await interaction.followup.send(embed=embed, file=file)


async def setup(bot: commands.Bot):
    await bot.add_cog(ImageCog(bot))
