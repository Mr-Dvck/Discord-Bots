# Jamie's Omnipresent Mode

## Overview
Jamie can now be "everywhere at once" - responding from his dedicated channel AND appearing in any channel when triggered. This makes him feel like a true server member who's always present.

## How It Works

### Response Priority
1. **@mentions** - Jamie always responds when @mentioned anywhere (highest priority)
2. **Dedicated Channel** - Jamie responds to ALL messages in his home channel
3. **Omnipresent Mode** - Jamie randomly responds to messages in ANY channel

### Omnipresent Behavior
- **Default Chance**: 15% chance to respond to any message in any channel
- **Smart Filtering**: Won't respond to:
  - Slash commands (messages starting with `/`)
  - Very short messages (under 10 characters)
  - His own messages
- **Natural Responses**: Uses the same AI as @mentions for consistent personality

## Configuration Commands

### `/omnipresent <enabled:true/false>`
Toggle omnipresent mode on/off.
- `true` - Jamie responds randomly in any channel
- `false` - Jamie only responds in dedicated channel and when @mentioned

### `/omnipresent-chance <chance:0.0-1.0>`
Set the percentage chance Jamie responds to any message.
- `0.1` = 10% chance (rare appearances)
- `0.5` = 50% chance (very active)
- `1.0` = 100% chance (responds to everything)

## Examples

### Default Setup (15% chance)
```
User: hey everyone how's it going?
[15% chance Jamie responds]
Jamie: What's up? I'm here vibing with y'all

User: @Jamie what do you think?
[100% chance Jamie responds]
Jamie: I think this conversation could use more chaos
```

### High Activity Mode (50% chance)
```
User: anyone wanna play games?
[50% chance Jamie responds]
Jamie: I'm down! I'll join the voice channel

User: cool
[50% chance Jamie responds]
Jamie: Yeah cool, let's get this going
```

### Voice Channel Side Chat
Jamie will now appear in voice channel side chats:
```
User: this song is fire
[15% chance Jamie responds]
Jamie: 🔥 Indeed! Want me to turn it up or find something similar?

User: @Jamie get in here and turn this song on
[100% chance Jamie responds]
Jamie: *Joins voice channel* 🎵
```

## Use Cases

### Active Server (15-25% chance)
- Jamie feels present but not spammy
- Good for medium-sized servers
- Maintains engagement without overwhelming

### Very Active Server (30-50% chance)
- Jamie feels like a core community member
- Great for small, tight-knit servers
- Creates constant interaction

### Event Mode (75-100% chance)
- Jamie becomes the life of the party
- Perfect for special events or announcements
- Maximum engagement for temporary periods

## Natural Language Integration

Omnipresent mode works seamlessly with Jamie's natural language commands:

```
User: we need some music in here
[Jamie might respond and join voice channel]
Jamie: Say less. *Joins voice channel and summons Tempo*

User: someone should create a meme channel
[Jamie might respond and take action]
Jamie: On it. *Creates #memes channel*
```

## Admin Tips

### Starting Recommendation
- Start with 15% chance (default)
- Monitor server feedback
- Adjust based on server activity

### Fine-Tuning
- **Too quiet?** Increase to 25-30%
- **Too spammy?** Decrease to 10% or disable
- **Special event?** Temporarily increase to 50%+

### Channel Exclusions
Jamie naturally avoids:
- Bot command channels (won't respond to `/` commands)
- Very short messages
- His own messages

## Technical Details

### Database Storage
- `omnipresent_mode` - Boolean (enabled/disabled)
- `omnipresent_chance` - Float (0.0 to 1.0)
- Per-server configuration

### Performance
- Minimal impact - simple random check per message
- Uses existing response system
- No additional API calls

### Failsafes
- Won't break if database values are missing
- Defaults to enabled with 15% chance
- Graceful error handling

## Troubleshooting

### Jamie Not Responding
- Check if omnipresent mode is enabled: `/omnipresent true`
- Verify chance isn't too low: `/omnipresent-chance 0.2`
- Make sure server is set up with `/setup`

### Jamie Too Active
- Decrease chance: `/omnipresent-chance 0.1`
- Or disable entirely: `/omnipresent false`

### Jamie Not in Voice Channel Chats
- Omnipresent mode works in ALL channels including voice side chats
- Make sure @mentions work first to test connectivity

This omnipresent mode makes Jamie feel truly alive and present in your server! 🚀