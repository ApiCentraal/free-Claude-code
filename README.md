# Free Claude Code

Run Claude Code for free using NVIDIA's free-tier API keys with automatic key rotation.

> This is a fork of [claude-code-haha](https://github.com/NanmiCoder/claude-code-haha) with added Keymaster integration for free API usage.

## Overview

This project lets you run Claude Code locally without paying for API access by:
- Using NVIDIA's free-tier API keys (nvapi-...)
- Rotating through multiple keys automatically when rate limits hit
- Running a local bridge that translates Anthropic API calls to OpenAI-compatible format

## Quick Start

### Option 1: Automated Setup (Recommended)

Run the setup wizard:

```bash
python3 setup_wizard.py
```

The wizard will:
1. Install all dependencies
2. Collect your NVIDIA API keys
3. Configure Keymaster for key rotation
4. Set up Chrome for web tools
5. Start all services
6. Launch Claude Code

### Option 2: Manual Setup

See [WIZARD.md](WIZARD.md) for detailed manual setup instructions.

## Getting NVIDIA API Keys

1. Go to https://build.nvidia.com
2. Create accounts and generate API keys (format: `nvapi-...`)
3. You need at least 5 keys for reliable rotation
4. **Need more emails?** Use https://www.agentmail.to for throwaway inboxes (free plan = 3 inboxes at once)

## Architecture

```
┌─────────────┐      Anthropic API      ┌──────────────┐      OpenAI API      ┌─────────────┐
│  Claude     │ ───────────────────────> │   simple_    │ ──────────────────> │  Keymaster  │
│  Code TUI   │    (local bridge)        │   bridge.py  │                     │  (port 8787)│
└─────────────┘                          └──────────────┘                     └──────┬──────┘
                                                                                      │
                                                                           Rotates keys │
                                                                           to NVIDIA API
                                                                                      ▼
                                                                             ┌─────────────┐
                                                                             │  NVIDIA API │
                                                                             │  (free tier)│
                                                                             └─────────────┘
```

## Components

| Component | Purpose | Port |
|-----------|---------|------|
| `simple_bridge.py` | Translates Anthropic ↔ OpenAI API | 8789 |
| Keymaster | Rotates NVIDIA API keys | 8787 |
| Chrome | Web tools (fetch/search) | 9222 |

## Commands

### Keymaster
```bash
keymaster status      # Current status
keymaster health      # Health check
keymaster keys        # List keys
keymaster logs        # Follow logs
keymaster cooldowns   # Show rate-limited keys
keymaster reset       # Clear all cooldowns
```

### Services
```bash
# Chrome debug port
sudo systemctl status chrome-debug
sudo systemctl restart chrome-debug

# Simple bridge
sudo systemctl status simple-bridge
sudo systemctl restart simple-bridge

# Keymaster
keymaster start
keymaster stop
keymaster restart
```

### Claude Code
```bash
# Start TUI
./bin/claude-haha

# Headless mode
./bin/claude-haha -p "your prompt"

# Recovery CLI (if TUI fails)
CLAUDE_CODE_FORCE_RECOVERY_CLI=1 ./bin/claude-haha
```

## Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| API Keys | `~/.openclaw/agents/main/agent/auth-profiles.json` | NVIDIA key storage |
| OpenClaw Config | `~/.openclaw/openclaw.json` | Model routing & settings |
| Keymaster | `~/.openclaw/skills/keymaster/` | Key rotation proxy |

## Troubleshooting

### Keymaster Issues
```bash
# Check logs
tail -n 50 ~/.openclaw/keymaster.log
journalctl -u openclaw-keymaster@$USER -n 50

# Validate auth config
python3 -m json.tool ~/.openclaw/agents/main/agent/auth-profiles.json
```

### Chrome Debug Port
```bash
# Check service
sudo systemctl status chrome-debug
journalctl -u chrome-debug -n 50

# Test port
curl http://localhost:9222/json/version
```

### Bridge Issues
```bash
# Check service
sudo systemctl status simple-bridge
journalctl -u simple-bridge -n 50

# Test manually
curl http://localhost:8789/health
```

## Model Support

Currently configured for `moonshotai/kimi-k2.5` via the NVIDIA API. The model mapping happens in `simple_bridge.py`:

```python
MODEL_MAP = {
    "claude-sonnet-4-6": "moonshotai/kimi-k2.5",
    "claude-opus-4-6": "moonshotai/kimi-k2.5",
    # ... etc
}
```

## Security Notes

- **Never commit `auth-profiles.json`** - it contains your API keys
- Keys are stored locally in `~/.openclaw/`
- The setup wizard backs up existing configs before modifying them

## Original Project

This fork is based on [NanmiCoder/claude-code-haha](https://github.com/NanmiCoder/claude-code-haha), which fixed the original leaked Claude Code source to make it runnable.

## Disclaimer

This project uses the leaked Claude Code source (2026-03-31) from Anthropic's npm registry. All original source code copyright belongs to [Anthropic](https://www.anthropic.com). For educational and research purposes only.

The NVIDIA API integration uses NVIDIA's free tier which has rate limits. Respect their terms of service.
