# Jamie's Natural Language Commands

## Overview
Jamie now understands natural language commands instead of requiring slash commands! Just talk to Jamie like you would to a friend.

## How It Works
When you @mention Jamie or talk in his dedicated channel, he uses AI to understand your request and automatically calls the right functions. No more memorizing slash commands!

## Natural Language Examples

### Voice & Music Commands
```
@Jamie get in here and turn this song on
@Jamie join the voice channel
@Jamie summon tempo
@Jamie play some lofi music
@Jamie put on the chill playlist
@Jamie pause the music
@Jamie skip this song
@Jamie turn up the volume to 50
@Jamie leave voice chat
```

### Server Management
```
@Jamie create a new voice channel called "Gaming"
@Jamie make a text channel for memes
@Jamie create a role called "VIP" with color red
@Jamie kick that spammer
@Jamie ban the troublemaker
@Jamie timeout that user for 10 minutes
```

### Information & Help
```
@Jamie what channels do we have?
@Jamie show me all the roles
@Jamie list some members
@Jamie what's the server map look like?
@Jamie tell me about @username
```

### Custom Characters (if enabled)
```
@Jamie cynthia: tell me a story
@Jamie nyx: what do you see in the shadows?
```

## Key Features

### Smart Context Understanding
- Jamie understands context from your conversation
- He knows what channel you're in
- He remembers previous messages in the conversation
- He can reference users by name or @mention

### Flexible Phrasing
- Multiple ways to say the same thing
- Casual language works perfectly
- No need to remember exact command syntax
- Jamie figures out what you mean

### Error Handling
- If Jamie can't understand, he'll ask for clarification
- He'll tell you if he lacks permissions
- Clear feedback when something goes wrong

### Tool Integration
- Voice channel management
- Music bot control (Tempo integration)
- Server administration (admin only)
- Information retrieval
- Custom character interactions

## Examples in Action

### Scenario 1: Setting Up Music
```
User: @Jamie get in the music vc and put on some chill beats
Jamie: *Joins Music voice channel* ✅
Jamie: *Summons Tempo* ✅  
Jamie: *Playing chill beats* ✅
```

### Scenario 2: Quick Server Management
```
User: @Jamie make a new channel for gaming talk
Jamie: Creating #gaming-talk channel ✅
User: @Jamie create a VIP role
Jamie: Created VIP role with default color ✅
```

### Scenario 3: Information Request
```
User: @Jamie what's this server all about?
Jamie: This server has 15 channels, 3 categories, 42 members...
```

## Tips for Best Results

### Be Specific but Natural
- ✅ "Join the music channel and play lofi"
- ❌ "Join music channel" then "Play lofi" (two separate messages)

### Use Context
- If you're in a voice channel: "Play some music" (Jamie knows which one)
- If you mention a user: "Give @username the VIP role"

### Admin Commands
- Sensitive actions (kick, ban, timeout) require admin permissions
- Jamie will verify permissions before executing

### Music Control
- Jamie works with Tempo music bot
- Can join empty voice channels
- Supports playlists and individual songs
- Volume control and playback management

## Behind the Scenes
Jamie uses:
- **LLM Analysis**: Understands natural language intent
- **Tool Calling**: Maps requests to Discord API functions
- **Context Awareness**: Uses conversation history and server state
- **Permission Checking**: Verifies user permissions before actions
- **Error Recovery**: Graceful handling when things go wrong

This makes Jamie feel like a real server member who understands natural conversation rather than a command-line bot!