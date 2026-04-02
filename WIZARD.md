# Claude Code Setup Wizard

This wizard automates the installation and configuration of `claude-code-haha` with Keymaster for free NVIDIA API-based usage.

## What the Wizard Does

1. **Warns before wiping** - Gives you a chance to save any work
2. **Sets up Python venv** - Creates `~/.venv` and installs dependencies
3. **Removes existing Claude** - Safely wipes any existing Claude Code installation
4. **Installs Keymaster** - Sets up the API key rotation proxy
5. **Collects NVIDIA keys** - Interactively gathers your free-tier NVIDIA API keys
6. **Configures everything** - Writes auth profiles and merges with existing config
7. **Installs Chrome** - Sets up Chrome/Chromium with debug port 9222
8. **Starts services** - Creates systemd services for Chrome and simple_bridge
9. **Launches Claude** - Starts the TUI as the final step

## Quick Start

```bash
# From the project directory
python3 setup_wizard.py

# Or use the wrapper
./bin/setup-wizard
```

## Prerequisites

- Linux system with systemd
- Python 3.8+
- sudo privileges (for installing Chrome and creating systemd services)
- Git
- At least 5 free NVIDIA API keys from https://build.nvidia.com

## Getting NVIDIA API Keys

1. Go to https://build.nvidia.com
2. Sign up with different email accounts
3. Generate API keys (format: `nvapi-...`)
4. The wizard will prompt you for these keys

**Need more emails?** Use https://www.agentmail.to for throwaway inboxes (free plan allows 3 at once).

## What Gets Installed

| Component | Location |
|-----------|----------|
| Python venv | `~/.venv` |
| Keymaster | `~/.openclaw/skills/keymaster/` |
| API keys config | `~/.openclaw/agents/main/agent/auth-profiles.json` |
| OpenClaw config | `~/.openclaw/openclaw.json` |
| Chrome service | `/etc/systemd/system/chrome-debug.service` |
| Bridge service | `/etc/systemd/system/simple-bridge.service` |

## After Setup

The wizard automatically launches Claude. You can also start it manually:

```bash
./bin/claude-haha
```

### Useful Keymaster Commands

```bash
keymaster status      # Current status
keymaster health      # Health check
keymaster keys        # List keys
keymaster logs        # Follow logs
keymaster cooldowns   # Show rate-limited keys
keymaster reset       # Clear all cooldowns
```

### Service Management

```bash
# Chrome debug port
sudo systemctl status chrome-debug
sudo systemctl restart chrome-debug

# Simple bridge
sudo systemctl status simple-bridge
sudo systemctl restart simple-bridge

# Keymaster (runs as user service)
keymaster start
keymaster stop
keymaster restart
```

## Troubleshooting

### Keymaster not starting

```bash
# Check logs
tail -n 50 ~/.openclaw/keymaster.log
journalctl -u openclaw-keymaster@$USER -n 50

# Validate auth config
python3 -m json.tool ~/.openclaw/agents/main/agent/auth-profiles.json
```

### Chrome debug port not responding

```bash
# Check service
sudo systemctl status chrome-debug
journalctl -u chrome-debug -n 50

# Test port
curl http://localhost:9222/json/version
```

### Bridge not starting

```bash
# Check service
sudo systemctl status simple-bridge
journalctl -u simple-bridge -n 50

# Test manually
source ~/.venv/bin/activate
python3 simple_bridge.py
```

## Re-running the Wizard

You can safely re-run the wizard at any time. It will:
- Preserve existing config (with backup)
- Only reinstall if needed
- Skip healthy services

## Security Notes

- **Never commit `auth-profiles.json`** - it contains your API keys
- The wizard backs up existing configs before modifying them
- All keys stay local in `~/.openclaw/`
