# 🔥 Jamie Discord Bot

A sentient Discord bot that memorizes every user, maps the entire server, monitors conversations, and talks back with personality. Comes with a Dyno-style web dashboard for server management.

## Features

- **🛸 Auto Setup** — When Jamie joins a server, it asks for a dedicated channel via `/setup`
- **🧠 Memory System** — Memorizes every username, tracks message counts, builds personality profiles
- **🗺️ Server Cartography** — Maps all channels, categories, and structure automatically
- **💬 Smart Chat** — Responds in dedicated channel or when @mentioned, with full context awareness
- **🎨 Image Generation** — `/generate` and `/imagine` commands for AI image creation
- **📋 User Profiles** — `/profile` shows everything Jamie knows about a user
- **🔍 Memory Search** — `/remember` searches Jamie's message memory
- **📊 Stats** — `/stats` shows server engagement metrics
- **🖥️ Web Dashboard** — Dyno-style management UI with Jamie chat widget

## Bot Commands

| Command | Description |
|---------|-------------|
| `/setup` | Set Jamie's dedicated channel (admin) |
| `/setchannel` | Change Jamie's channel (admin) |
| `/talk <message>` | Talk to Jamie directly |
| `/ask <query>` | Ask about someone/something |
| `/generate <prompt>` | Generate an image |
| `/imagine` | Jamie imagines something wild |
| `/profile [user]` | View a user's profile |
| `/servermap` | View the server map |
| `/remember <query>` | Search Jamie's memory |
| `/note <user> <note>` | Add a note to a user (admin) |
| `/stats` | View server statistics |
| `/help` | Show all commands |

## Dashboard

The web dashboard mimics Dyno's setup with a dark theme and includes:

- **📊 Dashboard** — Overview of all servers, stats, quick actions
- **🗺️ Servers** — Browse and manage individual servers (channels, roles, members)
- **🏗️ Server Builder** — Build or revamp entire servers from scratch (AI-generated or manual)
- **⚙️ Modules** — Toggle and configure Jamie's modules (moderation, welcome, levels, etc.)
- **🔥 Jamie Chat** — Private chat with Jamie in the bottom-right corner for configuration help

### Dashboard Pages

| Page | Description |
|------|-------------|
| `/` | Dashboard home with server list and stats |
| `/servers` | All servers overview |
| `/servers/[id]` | Server detail: channels, roles, members management |
| `/builder` | Server builder (AI generate or manual) |
| `/modules` | Module configuration |

### Dashboard API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/guilds` | GET | List all bot guilds |
| `/api/guilds/[id]` | GET | Get guild details (channels, roles, members) |
| `/api/guilds/[id]/channels` | POST/PATCH/DELETE | Create/modify/delete channels |
| `/api/guilds/[id]/roles` | POST/PATCH/DELETE | Create/modify/delete roles |
| `/api/guilds/[id]/build` | POST | Bulk build server from blueprint |
| `/api/chat` | POST | Chat with Jamie (LLM) |
| `/api/generate-blueprint` | POST | AI-generate server blueprint |

## Setup

### Bot Setup
1. Install Python 3.10+
2. Run `start.bat` (Windows) — auto-creates venv and installs deps
3. Invite Jamie to your server with bot + applications.commands permissions
4. Run `/setup` in your server

### Dashboard Setup (Local)
1. Install Node.js 18+
2. The `start.bat` script launches both bot and dashboard
3. Dashboard runs at `http://localhost:3000`

### Dashboard Deployment (Vercel)
1. Push the `dashboard/` directory to GitHub
2. Connect the repo to Vercel
3. Set environment variables in Vercel:
   - `DISCORD_BOT_TOKEN_JAMIE`
   - `OPENROUTER_API_KEY`
   - `JAMIE_LLM_MODEL`
   - `JAMIE_LLM_API_BASE`
4. Deploy

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DISCORD_BOT_TOKEN_JAMIE` | Discord bot token |
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM |
| `JAMIE_LLM_MODEL` | LLM model name (default: meta-llama/llama-3.3-70b-instruct) |
| `JAMIE_LLM_API_BASE` | LLM API base URL |
| `JAMIE_APP_ID` | Discord application ID (optional, for slash commands) |

## Architecture

```
Jamie/
├── main.py              # Bot entry point
├── .env                 # Environment variables
├── requirements.txt     # Python dependencies
├── start.bat/sh         # Launch scripts (bot + dashboard)
├── db/
│   ├── database.py      # SQLite async database layer
│   └── __init__.py
├── llm/
│   ├── client.py        # OpenRouter LLM client
│   └── __init__.py
├── image/
│   ├── generator.py     # Pollinations.ai image generator
│   └── __init__.py
├── cogs/
│   ├── setup.py         # Server setup & channel config
│   ├── memory.py        # Message monitoring & user profiling
│   ├── chat.py          # Conversation engine
│   ├── image_cog.py     # Image generation commands
│   ├── utility.py       # Profile, servermap, remember, stats
│   └── __init__.py
├── data/
│   └── jamie.db         # SQLite database (auto-created)
└── dashboard/            # Next.js web dashboard
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx              # Dashboard home
    │   │   ├── layout.tsx           # Root layout
    │   │   ├── globals.css           # Dyno dark theme
    │   │   ├── servers/page.tsx      # Servers list
    │   │   ├── servers/[id]/page.tsx # Server detail
    │   │   ├── builder/page.tsx      # Server builder
    │   │   ├── modules/page.tsx      # Module config
    │   │   └── api/                  # API routes
    │   │       ├── guilds/           # Guild CRUD
    │   │       ├── chat/             # Jamie chat
    │   │       └── generate-blueprint/ # AI blueprint
    │   ├── components/
    │   │   ├── Sidebar.tsx           # Navigation sidebar
    │   │   └── JamieChat.tsx         # Chat widget
    │   └── lib/
    │       ├── discord.ts            # Discord API client
    │       └── llm.ts                # LLM client
    ├── vercel.json
    └── package.json
```

## How It Works

1. **First Join**: Jamie lands in a server → DMs the owner + posts asking for `/setup`
2. **`/setup #channel`**: Sets Jamie's dedicated channel, triggers full server cartography, registers all members
3. **Memory System**: Every message stored in SQLite. Background tasks analyze user personalities via LLM every 30 min
4. **Conversations**: Jamie responds in its dedicated channel or when @mentioned, using full user context + conversation history
5. **Images**: `/generate <prompt>` uses LLM to enhance prompt → Pollinations.ai generates (free, no API key)
6. **Dashboard**: Web UI for managing servers, building new ones, configuring modules, and chatting with Jamie
7. **Server Builder**: Describe what you want → AI generates a blueprint → Apply it to build channels/roles automatically

## Part of the BCR Factory Ecosystem
