# Using Keymaster with Claude Code

This setup routes Claude Code through Keymaster's NVIDIA key rotation system.

## Architecture

```
Claude Code (port 8788) → Anthropic Bridge → Keymaster (port 8787) → NVIDIA API
```

## Prerequisites

1. Keymaster is installed and running (`~/.openclaw/skills/keymaster/`)
2. Python 3.10+ with dependencies: `pip install fastapi uvicorn httpx`

## Quick Start

### Step 1: Start Keymaster (if not running)

```bash
~/.openclaw/skills/keymaster/keymaster start
```

Verify it's running:
```bash
~/.openclaw/skills/keymaster/keymaster status
```

### Step 2: Start the Anthropic Bridge

```bash
# From this directory
python anthropic_bridge.py
```

The bridge will start on port 8788 and connect to Keymaster on port 8787.

### Step 3: Configure Claude Code Environment

The `.env` file is already configured:

```bash
ANTHROPIC_BASE_URL=http://127.0.0.1:8788
ANTHROPIC_AUTH_TOKEN=dummy-keymaster-handles-auth
DISABLE_TELEMETRY=1
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

### Step 4: Run Claude Code

```bash
export PATH="$HOME/.bun/bin:$PATH"
bun run ./src/entrypoints/cli.tsx --bare --print "Hello"
```

## Model Mapping

The bridge maps Anthropic model names to NVIDIA models:

| Anthropic Model | NVIDIA Model |
|----------------|--------------|
| claude-sonnet-4-6 | nvidia/llama-3.1-405b-instruct |
| claude-opus-4-6 | nvidia/llama-3.1-405b-instruct |
| claude-haiku-4-5 | nvidia/llama-3.1-70b-instruct |
| claude-3-sonnet | nvidia/llama-3.1-70b-instruct |
| claude-3-opus | nvidia/llama-3.1-405b-instruct |
| sonnet | nvidia/llama-3.1-70b-instruct |
| opus | nvidia/llama-3.1-405b-instruct |
| haiku | nvidia/llama-3.1-8b-instruct |

## How It Works

1. **Claude Code** sends Anthropic API format requests to the bridge
2. **Anthropic Bridge** converts requests to OpenAI format
3. **Keymaster** receives OpenAI requests and rotates through your 5 NVIDIA API keys
4. **NVIDIA API** processes the request and returns responses
5. **Bridge** converts OpenAI responses back to Anthropic format
6. **Claude Code** receives responses as if from Anthropic

## Troubleshooting

### Check Bridge Health
```bash
curl http://127.0.0.1:8788/health
```

### Check Keymaster Health
```bash
curl http://127.0.0.1:8787/health
```

### View Logs

Keymaster logs:
```bash
~/.openclaw/skills/keymaster/keymaster logs
```

Bridge logs: Check terminal where `anthropic_bridge.py` is running

### Test Directly

Test the bridge:
```bash
curl -X POST http://127.0.0.1:8788/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sonnet",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100,
    "stream": false
  }'
```

## Benefits

- **Automatic key rotation**: When one key hits rate limits, Keymaster switches to the next
- **5 key slots**: Uses primary, secondary, tertiary, quaternary, quinary keys
- **No interruption**: Conversations continue seamlessly across key switches
- **Long-running tasks**: Can run for hours without manual intervention
