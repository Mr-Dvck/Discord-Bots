# Jamie Bot Feature Ideas Tracker

Here is a log of user ideas and feature requests captured during pair-programming sessions.

## 🚀 Active Concepts

### 1. Multi-Character AI Engine (Webhook Integration)
- **Concept:** Like MEE6's multi-character chat features, allow creating multiple custom personalities (e.g. Cynthia, Bobby, Toby) with distinct avatars and prompt systems.
- **Implementation:** 
  - Store characters in a SQLite table `custom_personalities` (name, avatar_url, system_prompt).
  - Use Discord Webhooks to post replies in channels. Webhooks allow the bot to send a message using *any* arbitrary username and avatar icon dynamically on the fly.
  - Chat interface: Trigger specific characters using a `/talk_as` slash command, or when mentioning the character by name.

### 2. Auto-Discovery & Dynamic Command Enabling
- **Concept:** Have commands automatically add themselves to the dashboard config registry as they are executed, keeping the initial configurations clean.
- **Implementation:** Write a helper decorator or tree event that registers command usage metrics into `guild_settings.commands_json` dynamically if a command does not already exist.

---
*Created: 2026-07-17*
