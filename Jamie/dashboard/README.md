# 🔥 Jamie Dashboard

A Dyno-style web dashboard for managing the Jamie Discord bot. Built with Next.js 16, TypeScript, and Tailwind CSS.

## Features

- **📊 Dashboard** — Overview of all servers, stats, quick actions
- **🗺️ Servers** — Browse and manage individual servers (channels, roles, members)
- **🏗️ Server Builder** — Build or revamp entire servers from scratch (AI-generated or manual)
- **⌨️ Commands** — Full slash catalog (`/economy`, `/mod`, `/manage`, `/misc`, …)
- **⚙️ Modules** — Toggle command packs (moderation, economy, ranks, misc, …)
- **🔥 Jamie Chat** — Private chat that can operate the dashboard via tools

## Deploy on Vercel

1. Push this repo to GitHub
2. Connect to Vercel
3. Set environment variables:
   - `DISCORD_BOT_TOKEN_JAMIE` — Your Discord bot token
   - `OPENROUTER_API_KEY` — OpenRouter API key for LLM
   - `JAMIE_LLM_MODEL` — LLM model (e.g. `meta-llama/llama-3.3-70b-instruct`)
   - `JAMIE_LLM_API_BASE` — LLM API base URL (e.g. `https://openrouter.ai/api/v1`)
4. Deploy

## Local Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/guilds` | GET | List all bot guilds |
| `/api/guilds/[id]` | GET | Guild details (channels, roles, members) |
| `/api/guilds/[id]/channels` | POST/PATCH/DELETE | Channel CRUD |
| `/api/guilds/[id]/roles` | POST/PATCH/DELETE | Role CRUD |
| `/api/guilds/[id]/build` | POST | Bulk build server from blueprint |
| `/api/chat` | POST | Chat with Jamie |
| `/api/generate-blueprint` | POST | AI-generate server blueprint |
