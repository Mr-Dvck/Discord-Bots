# Jamie's Music & Voice Control

## Overview
Jamie can now join voice channels, summon Tempo (music bot), and manage playlists - even in empty voice channels!

## Setup Requirements

### Bot Permissions
Make sure Jamie has these permissions:
- **Connect** to voice channels
- **Speak** in voice channels  
- **Read Messages** in text channels (for Tempo commands)
- **Send Messages** in text channels (for Tempo commands)

### Dependencies
The bot now includes:
- `PyNaCl` - For voice connections
- `youtube-dl` - For music URL support

## Commands

### Voice Channel Control
```
/join [channel]           # Join a voice channel (or your current one)
/leave                    # Leave the current voice channel
```

### Tempo Integration
```
/summon-tempo             # Summon Tempo to Jamie's voice channel
```

### Music Control
```
/play <song/URL>          # Play a specific song
/playlist <name/URL>      # Load a playlist
/pause                    # Pause current song
/resume                   # Resume paused song
/skip                     # Skip current song
/stop                     # Stop music completely
/volume <0-100>           # Set volume level
```

## Usage Examples

### Basic Setup
1. `/join General` - Jamie joins the General voice channel
2. `/summon-tempo` - Summon Tempo to the same channel
3. `/play lofi hip hop` - Start playing music

### Empty VC Usage
Jamie can join and use music in empty voice channels:
1. `/join Empty VC` - Join even if no one is there
2. `/summon-tempo` - Bring Tempo in
3. `/playlist "Chill Vibes"` - Load your playlist
4. Jamie will stay for 5 minutes after everyone leaves, then auto-leave

### Playlist Control
```
/playlist "My Favorites"           # Load named playlist
/playlist https://youtube.com/...   # Load YouTube playlist
/play "Never Gonna Give You Up"     # Play specific song
/play https://youtube.com/...        # Play YouTube URL
```

## Tempo Command Compatibility

The system tries multiple command formats to work with different Tempo configurations:
- `!play`, `-play`, `/play`, `t!play`, `tempo play`
- `!playlist`, `-playlist`, `/playlist`, `t!playlist`, `tempo playlist`
- `!summon`, `-summon`, `/summon`, `t!summon`, `tempo summon`
- `!pause`, `!resume`, `!skip`, `!stop`, `!volume`

## Features

### Smart Voice Management
- Jamie automatically leaves empty voice channels after 5 minutes
- Maintains voice connections per guild
- Handles permission checks before joining

### Tempo Detection
- Automatically finds Tempo in the server
- Caches Tempo's user ID for faster commands
- Works with any Tempo bot name containing "tempo"

### Error Handling
- Graceful fallbacks if commands fail
- Clear error messages for missing permissions
- Automatic cleanup on disconnect

## Troubleshooting

### Tempo Not Found
- Make sure Tempo is invited to the server
- Check Tempo has Read Messages permission
- Use `/summon-tempo` to refresh Tempo detection

### Voice Connection Issues
- Verify Jamie has Connect and Speak permissions
- Check voice channel isn't full
- Ensure Jamie isn't already connected elsewhere

### Command Failures
- Tempo might use different command prefixes
- Check Tempo has Send Messages permission
- Try different song/playlist name formats

## Tips

### Best Practices
1. Join a voice channel first, then summon Tempo
2. Use descriptive playlist names for easier loading
3. Jamie works best in dedicated music channels
4. Set appropriate volume levels (0-100)

### Advanced Usage
- Jamie can manage multiple voice channels across different guilds
- Use in empty VCs for background music
- Combine with behavior personas for themed music sessions

This system gives you full control over music playback while maintaining Jamie's personality and features!