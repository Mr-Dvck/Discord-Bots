#!/usr/bin/env python3
"""
Quick script to send Jamie to a specific channel
"""
import discord
import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv('.env')

async def send_jamie_to_channel():
    # Create bot instance with same configuration as main bot
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True
    intents.messages = True
    intents.typing = True
    intents.presences = False
    intents.voice_states = True
    
    bot = discord.Client(intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'Bot connected as {bot.user}')
        
        # Find the guild
        guild_id = 1139997451835674667
        guild = bot.get_guild(guild_id)
        
        if guild:
            print(f'Found guild: {guild.name}')
            
            # List all text channels
            print('Available text channels:')
            for channel in guild.text_channels:
                print(f'  - {channel.name} (ID: {channel.id})')
            
            # Try to find the target channel
            target_channel_id = 1526807732924059658
            target_channel = guild.get_channel(target_channel_id)
            
            if target_channel:
                print(f'Found target channel: {target_channel.name}')
                try:
                    # Send the message
                    await target_channel.send('we\'ll be with you shortly')
                    print(f'Successfully sent message to {target_channel.name}')
                except discord.Forbidden:
                    print(f'ERROR: No permission to send messages to {target_channel.name}')
                    print('Jamie needs "Send Messages" permission in this channel')
                except Exception as e:
                    print(f'ERROR: {e}')
            else:
                print(f'ERROR: Target channel {target_channel_id} not found')
                print('Available channels:')
                for channel in guild.text_channels:
                    print(f'  {channel.name} (ID: {channel.id})')
        else:
            print(f'ERROR: Guild {guild_id} not found')
        
        await bot.close()
    
    # Connect and send
    token = os.getenv('DISCORD_BOT_TOKEN_JAMIE')
    if not token:
        print('ERROR: No Discord token found in .env file')
        return
    
    try:
        await bot.start(token)
    except Exception as e:
        print(f'ERROR: Failed to connect: {e}')

if __name__ == '__main__':
    asyncio.run(send_jamie_to_channel())