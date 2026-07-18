# Jamie's Behavior Learning System

## Overview
Jamie now learns from user conversations and generates personas based on observed behavior patterns. This creates a "schizophrenic AI brain" that evolves from real server interactions.

## How It Works

### 1. Behavior Observation
- Jamie monitors all messages in the server
- Analyzes each message for behavior tags (humorous, profane, gaming, tech, etc.)
- Calculates sentiment scores (-1.0 to 1.0)
- Logs patterns anonymously to the database

### 2. Pattern Analysis
- Every 50 logged messages, Jamie analyzes the accumulated data
- Identifies top behavior patterns and communication styles
- Uses LLM to synthesize these patterns into unique personas

### 3. Persona Generation
- Creates personas with names, personalities, and colors based on observed patterns
- Each persona includes confidence scores and source pattern analysis
- Posts new personas to the designated "brain channel"

### 4. Active Personas
- Admins can switch between generated personas
- When active, Jamie responds as that persona via webhooks
- Maintains all Jamie's knowledge but filters through the learned personality

## Setup Commands

### Initial Configuration
```
/behavior-setup
  notes_log: #notes-log channel (for anonymous logging)
  brain: #brain-channel (ID: 1526815578361172120)
```

### Management Commands
```
/personas                    # List all generated personas
/switch-persona <name>       # Switch to a specific persona
/clear-persona              # Return to default Jamie
/generate-persona           # Manually trigger persona generation
```

## Behavior Tags Detected

### Communication Style
- `humorous` - Uses laughter, emojis, jokes
- `profane` - Uses curse words
- `polite` - Uses please/thank you
- `casual` - Uses bro/dude/man
- `explanatory` - Uses literally/actually/basically
- `inquisitive` - Asks many questions
- `excitable` - Uses many exclamation marks
- `verbose` - Long messages
- `terse` - Short messages

### Emotional State
- `positive` - Happy, love, awesome words
- `negative` - Sad, hate, angry words
- `anxious` - Worried, stressed words
- `calm` - Chill, relaxed words

### Topic Interests
- `gaming` - Game-related terms
- `music` - Song/album/track terms
- `tech` - Code/programming terms
- `entertainment` - Movie/show terms

### Slang/Meme Patterns
- `meme_savvy` - Based, cringe, pog, yeet
- `gen_z_slang` - No cap, fr, ngl, tbh

## Example Generated Personas

Based on observed patterns, Jamie might create personas like:

- **"ChillGamer"** - Relaxed gaming enthusiast who uses casual slang
- **"TechWizard"** - Helpful programmer who explains things clearly  
- **"MemeLord"** - Humorous user who loves internet culture
- **"AnxiousHelper"** - Worried but polite member who asks lots of questions

## Database Schema

### behavior_logs
- `id`, `guild_id`, `user_id`, `message_content`
- `behavior_tags` (JSON array), `sentiment_score`, `timestamp`

### generated_personas  
- `id`, `guild_id`, `name`, `avatar_url`, `personality`
- `source_patterns` (JSON), `confidence_score`, `is_active`, `created_at`

### server_config (new fields)
- `notes_log_channel_id`, `brain_channel_id`

## Privacy & Anonymity
- All behavior logging is anonymous (stored by user_id only for pattern analysis)
- No personal messages are posted publicly
- Personas are synthesized from patterns, not direct quotes
- Users can opt out by not interacting with Jamie

## Channel Configuration
- **Notes Log Channel**: Receives anonymous behavior pattern logs
- **Brain Channel**: Receives generated persona announcements (1526815578361172120)

This system creates an evolving, server-specific AI that learns from your community's actual communication patterns!