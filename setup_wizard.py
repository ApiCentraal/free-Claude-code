#!/usr/bin/env python3
"""
Claude Code Setup Wizard
Installs and configures claude-code-haha with Keymaster, Chrome debug port, and simple_bridge.
"""

import os
import sys
import json
import subprocess
import time
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_colored(text: str, color: str = ""):
    """Print colored text."""
    if color:
        print(f"{color}{text}{Colors.END}")
    else:
        print(text)


def print_step(step_num: int, total: int, description: str):
    """Print a step header."""
    print()
    print_colored(f"{'='*60}", Colors.CYAN)
    print_colored(f"  STEP {step_num}/{total}: {description}", Colors.BOLD + Colors.CYAN)
    print_colored(f"{'='*60}", Colors.CYAN)
    print()


def run_command(cmd: List[str], capture: bool = True, check: bool = True, sudo: bool = False) -> Tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    if sudo and os.geteuid() != 0:
        cmd = ['sudo'] + cmd

    try:
        if capture:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, check=check)
            return result.returncode, "", ""
    except Exception as e:
        return 1, "", str(e)


def prompt_user(message: str, options: List[str] = None) -> str:
    """Prompt user for input with optional predefined options."""
    print()
    if options:
        print_colored(message, Colors.CYAN)
        for i, opt in enumerate(options, 1):
            print(f"  [{i}] {opt}")
        while True:
            choice = input(f"\nEnter choice (1-{len(options)}): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                return options[int(choice) - 1]
            print_colored("Invalid choice. Please try again.", Colors.WARNING)
    else:
        return input(f"{message} ").strip()


def confirm(message: str) -> bool:
    """Ask for yes/no confirmation."""
    while True:
        response = input(f"{message} (yes/no): ").strip().lower()
        if response in ('y', 'yes'):
            return True
        if response in ('n', 'no'):
            return False
        print("Please answer 'yes' or 'no'.")


def get_venv_path() -> Path:
    """Get or create Python virtual environment."""
    home = Path.home()
    venv_path = home / ".venv"

    if not venv_path.exists():
        print("Creating Python virtual environment at ~/.venv...")
        run_command([sys.executable, "-m", "venv", str(venv_path)], check=True)

    return venv_path


def get_venv_python() -> Path:
    """Get the Python executable path in the virtual environment."""
    venv = get_venv_path()
    if os.name == 'nt':
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def get_venv_pip() -> Path:
    """Get the pip executable path in the virtual environment."""
    venv = get_venv_path()
    if os.name == 'nt':
        return venv / "Scripts" / "pip.exe"
    return venv / "bin" / "pip"


def install_dependencies():
    """Install required Python packages into venv."""
    pip = get_venv_pip()
    deps = ['requests', 'playwright', 'psutil', 'httpx', 'websockets', 'fastapi', 'uvicorn']
    print(f"Installing dependencies: {', '.join(deps)}")
    code, out, err = run_command([str(pip), 'install'] + deps, check=True)
    if code != 0:
        print_colored(f"Failed to install dependencies: {err}", Colors.FAIL)
        sys.exit(1)
    print_colored("Dependencies installed successfully.", Colors.GREEN)


def wipe_claude_installation():
    """Remove existing Claude Code installation."""
    home = Path.home()
    paths_to_remove = [
        home / ".local" / "bin" / "claude",
        home / ".local" / "share" / "claude",
        home / ".claude",
        home / ".config" / "claude",
        home / ".cache" / "claude",
    ]

    for path in paths_to_remove:
        if path.exists():
            print(f"Removing: {path}")
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)

    # Verify removal
    remaining = [p for p in paths_to_remove if p.exists()]
    if remaining:
        print_colored(f"Warning: Could not remove: {remaining}", Colors.WARNING)
    else:
        print_colored("Claude Code installation removed.", Colors.GREEN)


def check_keymaster_exists() -> bool:
    """Check if Keymaster is already installed."""
    keymaster_dir = Path.home() / ".openclaw" / "skills" / "keymaster"
    return (keymaster_dir / ".git").exists()


def check_keymaster_health() -> bool:
    """Check if Keymaster service is healthy."""
    try:
        import requests
        response = requests.get("http://127.0.0.1:8787/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def check_auth_profiles() -> Tuple[bool, int]:
    """Check if auth profiles exist and have API keys."""
    auth_file = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "auth-profiles.json"
    if not auth_file.exists():
        return False, 0

    try:
        with open(auth_file) as f:
            data = json.load(f)
        profiles = data.get("profiles", {})
        api_keys = [p for p in profiles.values() if p.get("type") == "api_key"]
        return len(api_keys) > 0, len(api_keys)
    except:
        return False, 0


def is_systemd_service_active(service_name: str) -> bool:
    """Check if a systemd service is active."""
    code, out, _ = run_command(['systemctl', 'is-active', service_name], check=False)
    return code == 0 and 'active' in out


def clone_keymaster():
    """Clone or update Keymaster repository."""
    install_dir = Path.home() / ".openclaw" / "skills" / "keymaster"
    parent_dir = install_dir.parent

    if (install_dir / ".git").exists():
        print("Updating existing Keymaster...")
        run_command(['git', 'pull', 'origin', 'main'], cwd=str(install_dir), check=True)
    else:
        print("Cloning Keymaster...")
        parent_dir.mkdir(parents=True, exist_ok=True)
        run_command([
            'git', 'clone',
            'https://github.com/dommurphy155/Keymaster.git',
            str(install_dir)
        ], check=True)


def collect_nvidia_keys() -> List[str]:
    """Collect NVIDIA API keys from user."""
    print_colored("\n🔑 For Claude to work for free, you need at least 5 NVIDIA API keys (free tier).", Colors.BOLD)
    print_colored("Get your keys here: https://build.nvidia.com", Colors.CYAN)
    print()
    print_colored("💡 Don't have enough email accounts for 5 keys?", Colors.WARNING)
    print_colored("Use https://www.agentmail.to for throwaway emails.", Colors.WARNING)
    print_colored("(Free plan allows 3 inboxes at once - delete your existing 3 and create 3 more as needed.)", Colors.WARNING)
    print()

    keys = []
    while True:
        key_num = len(keys) + 1
        key = input(f"Key {key_num} (format: nvapi-... or press Enter if done): ").strip()

        if not key:
            if len(keys) >= 5:
                if not confirm("Do you have more keys to add?"):
                    break
            else:
                print_colored(f"You need at least 5 keys. Currently have {len(keys)}.", Colors.WARNING)
                continue

        if key.startswith("nvapi-"):
            keys.append(key)
            print_colored(f"✓ Key {key_num} recorded.", Colors.GREEN)
        elif key:
            print_colored("Invalid key format. Keys should start with 'nvapi-'", Colors.WARNING)

    return keys


def backup_openclaw_config():
    """Backup existing openclaw.json if it exists."""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if config_path.exists():
        backup_path = config_path.parent / f"openclaw.json.backup.{int(time.time())}"
        shutil.copy2(config_path, backup_path)
        print_colored(f"Backed up existing config to: {backup_path}", Colors.GREEN)
        return backup_path
    return None


def merge_openclaw_config(keys: List[str]):
    """Merge Keymaster configuration into openclaw.json."""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Build auth profiles config
    auth_config = {
        "profiles": {},
        "order": {"nvidia": []}
    }
    profile_names = ["nvidia:primary", "nvidia:secondary", "nvidia:tertiary",
                     "nvidia:quaternary", "nvidia:quinary"]

    for i, name in enumerate(profile_names[:len(keys)]):
        auth_config["profiles"][name] = {"provider": "nvidia", "mode": "api_key"}
        auth_config["order"]["nvidia"].append(name)

    # Build models config
    models_config = {"mode": "merge", "providers": {}}
    for i, key in enumerate(keys, 1):
        models_config["providers"][f"nvidia-key-{i}"] = {
            "baseUrl": "http://127.0.0.1:8787",
            "apiKey": key,
            "api": "openai-completions",
            "models": [{
                "id": "nvidia/nemotron-3-super-120b-a12b",
                "name": "Nemotron 3 Super",
                "reasoning": False,
                "input": ["text"],
                "cost": {"input": 0.000002, "output": 0.000008, "cacheRead": 0, "cacheWrite": 0},
                "contextWindow": 256000,
                "maxTokens": 16384
            }]
        }

    # Build agents config
    primary_model = f"nvidia-key-1/nvidia/nemotron-3-super-120b-a12b"
    fallbacks = [f"nvidia-key-{i}/nvidia/nemotron-3-super-120b-a12b" for i in range(2, len(keys) + 1)]

    models_aliases = {}
    for i in range(1, len(keys) + 1):
        models_aliases[f"nvidia-key-{i}/nvidia/nemotron-3-super-120b-a12b"] = {
            "alias": f"Nemotron 3 Super (Key {i})"
        }

    agents_config = {
        "defaults": {
            "model": {
                "primary": primary_model,
                "fallbacks": fallbacks
            },
            "models": models_aliases,
            "bootstrapMaxChars": 20000,
            "bootstrapTotalMaxChars": 150000,
            "compaction": {
                "mode": "safeguard",
                "reserveTokensFloor": 20000,
                "memoryFlush": {
                    "enabled": True,
                    "softThresholdTokens": 4000,
                    "systemPrompt": "Session nearing compaction. Store durable memories now.",
                    "prompt": "Write any lasting notes to memory/YYYY-MM-DD.md; reply with NO_REPLY if nothing to store."
                }
            },
            "timeoutSeconds": 86400,
            "maxConcurrent": 3,
            "subagents": {"maxConcurrent": 2}
        }
    }

    # Build tools config
    tools_config = {
        "profile": "full",
        "web": {
            "search": {"enabled": True},
            "fetch": {"enabled": True}
        },
        "loopDetection": {
            "enabled": True,
            "warningThreshold": 10,
            "criticalThreshold": 20,
            "globalCircuitBreakerThreshold": 30,
            "historySize": 30,
            "detectors": {
                "genericRepeat": True,
                "knownPollNoProgress": True,
                "pingPong": True
            }
        },
        "exec": {
            "backgroundMs": 10000,
            "timeoutSec": 86400,
            "cleanupMs": 1800000,
            "notifyOnExit": True,
            "notifyOnExitEmptySuccess": False,
            "applyPatch": {
                "enabled": True,
                "allowModels": ["nvidia/nemotron-3-super-120b-a12b:free"]
            }
        }
    }

    # Load existing config or create new
    if config_path.exists():
        with open(config_path) as f:
            existing = json.load(f)
    else:
        existing = {}

    # Merge configurations
    existing["auth"] = auth_config
    existing["models"] = models_config
    existing["agents"] = agents_config
    existing["tools"] = tools_config

    # Write merged config
    with open(config_path, 'w') as f:
        json.dump(existing, f, indent=2)

    print_colored(f"✓ Configuration written to: {config_path}", Colors.GREEN)


def write_auth_profiles(keys: List[str]):
    """Write auth-profiles.json with NVIDIA keys."""
    auth_dir = Path.home() / ".openclaw" / "agents" / "main" / "agent"
    auth_dir.mkdir(parents=True, exist_ok=True)

    profile_names = ["nvidia:primary", "nvidia:secondary", "nvidia:tertiary",
                     "nvidia:quaternary", "nvidia:quinary"]
    roles = ["coordinator", "strategist", "heavy_lifter", "worker", "fixer"]
    agent_mappings = ["main", "charlie", "echo", "alpha", "delta"]

    profiles = {}
    for i, key in enumerate(keys):
        name = profile_names[i] if i < len(profile_names) else f"nvidia:key_{i+1}"
        role = roles[i] if i < len(roles) else "worker"
        agent_map = agent_mappings[i] if i < len(agent_mappings) else "worker"

        # Build fallback chain
        fallback_chain = []
        for j in range(len(keys)):
            if j != i:
                fallback_chain.append(profile_names[j] if j < len(profile_names) else f"nvidia:key_{j+1}")

        fallback_to = fallback_chain[0] if fallback_chain else ""

        profiles[name] = {
            "type": "api_key",
            "provider": f"nvidia-key-{i+1}",
            "key": key,
            "priority": i + 1,
            "coordinator_priority": i + 1,
            "is_primary_coordinator": (i == 0),
            "can_act_as_coordinator": (i < 2),
            "role": role,
            "agent_mapping": agent_map,
            "model": "nvidia/nemotron-3-super-120b-a12b",
            "fallback_to": fallback_to,
            "fallback_chain": fallback_chain
        }

    auth_data = {
        "version": 1,
        "profiles": profiles,
        "lastGood": {"nvidia": "nvidia:primary"},
        "usageStats": {},
        "keymaster": {
            "enabled": True,
            "auto_rotation": True,
            "context_compaction": True,
            "compaction_threshold": 0.8,
            "cooldown_seconds": 60,
            "max_retries_per_key": 3,
            "state_persistence": True,
            "parallel_tool_calls": False,
            "timeout_seconds": 86400,
            "max_concurrent": 3
        }
    }

    auth_file = auth_dir / "auth-profiles.json"
    with open(auth_file, 'w') as f:
        json.dump(auth_data, f, indent=2)

    print_colored(f"✓ Auth profiles written to: {auth_file}", Colors.GREEN)


def install_keymaster():
    """Run Keymaster installer."""
    keymaster_dir = Path.home() / ".openclaw" / "skills" / "keymaster"
    install_script = keymaster_dir / "install.sh"

    if install_script.exists():
        print("Running Keymaster installer...")
        run_command(['bash', str(install_script)], cwd=str(keymaster_dir), check=True, capture=False)
    else:
        print_colored(f"Warning: install.sh not found at {install_script}", Colors.WARNING)


def start_keymaster_service():
    """Start Keymaster systemd service."""
    # Try keymaster command
    code, _, _ = run_command(['which', 'keymaster'], check=False)
    if code == 0:
        run_command(['keymaster', 'start'], check=False)
    else:
        # Try systemd directly
        user = os.environ.get('USER', os.environ.get('USERNAME', 'root'))
        run_command(['systemctl', 'start', f'openclaw-keymaster@{user}'], sudo=True, check=False)

    time.sleep(3)


def wait_for_keymaster_health(timeout: int = 60) -> bool:
    """Wait for Keymaster to become healthy."""
    print("Waiting for Keymaster to become healthy...")
    for _ in range(timeout):
        if check_keymaster_health():
            return True
        time.sleep(1)
    return False


def install_chrome() -> str:
    """Install Chrome or Chromium. Returns the executable name."""
    print("Installing Chrome/Chromium...")

    # Try Chrome first
    code, _, _ = run_command(['apt-get', 'install', '-y', 'google-chrome-stable'], sudo=True, check=False)
    if code == 0:
        print_colored("✓ Google Chrome installed.", Colors.GREEN)
        return "google-chrome"

    # Fallback to Chromium
    code, _, _ = run_command(['apt-get', 'install', '-y', 'chromium-browser'], sudo=True, check=False)
    if code == 0:
        print_colored("✓ Chromium installed.", Colors.GREEN)
        return "chromium-browser"

    # Try chromium as alternative name
    code, _, _ = run_command(['apt-get', 'install', '-y', 'chromium'], sudo=True, check=False)
    if code == 0:
        print_colored("✓ Chromium installed.", Colors.GREEN)
        return "chromium"

    print_colored("Warning: Could not install Chrome or Chromium automatically.", Colors.WARNING)
    return "google-chrome"  # Default to google-chrome anyway


def install_playwright():
    """Install Playwright Chromium."""
    print("Installing Playwright Chromium...")
    run_command([str(get_venv_pip()), 'install', 'playwright'], check=True)
    run_command([str(get_venv_python()), '-m', 'playwright', 'install', 'chromium'], check=True)
    print_colored("✓ Playwright Chromium installed.", Colors.GREEN)


def create_chrome_service(chrome_binary: str):
    """Create and start Chrome debug systemd service."""
    service_content = f"""[Unit]
Description=Chrome Remote Debugging on port 9222
After=network.target

[Service]
Type=simple
User=%i
ExecStart=/usr/bin/{chrome_binary} \
    --remote-debugging-port=9222 \
    --no-first-run \
    --no-default-browser-check \
    --disable-gpu \
    --headless
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

    service_path = Path("/etc/systemd/system/chrome-debug.service")

    # Write service file
    with open("/tmp/chrome-debug.service", 'w') as f:
        f.write(service_content)

    run_command(['cp', '/tmp/chrome-debug.service', str(service_path)], sudo=True, check=True)
    run_command(['systemctl', 'daemon-reload'], sudo=True, check=True)
    run_command(['systemctl', 'enable', 'chrome-debug'], sudo=True, check=True)
    run_command(['systemctl', 'start', 'chrome-debug'], sudo=True, check=True)

    time.sleep(3)

    # Check status
    code, out, _ = run_command(['systemctl', 'status', 'chrome-debug'], check=False)
    if 'active (running)' in out:
        print_colored("✓ Chrome debug service is running on port 9222.", Colors.GREEN)
    else:
        print_colored("Warning: Chrome debug service may not be running properly.", Colors.WARNING)


def create_bridge_service():
    """Create and start simple_bridge systemd service."""
    home = Path.home()
    venv_python = get_venv_python()
    bridge_script = home / "claude-code-haha" / "simple_bridge.py"

    service_content = f"""[Unit]
Description=Claude Code Simple Bridge
After=network.target chrome-debug.service

[Service]
Type=simple
User=%i
WorkingDirectory={home}/claude-code-haha
ExecStart={venv_python} {bridge_script}
Restart=always
RestartSec=5
Environment=KEYMASTER_URL=http://127.0.0.1:8787
Environment=CDP_URL=http://localhost:9222

[Install]
WantedBy=multi-user.target
"""

    service_path = Path("/etc/systemd/system/simple-bridge.service")

    with open("/tmp/simple-bridge.service", 'w') as f:
        f.write(service_content)

    run_command(['cp', '/tmp/simple-bridge.service', str(service_path)], sudo=True, check=True)
    run_command(['systemctl', 'daemon-reload'], sudo=True, check=True)
    run_command(['systemctl', 'enable', 'simple-bridge'], sudo=True, check=True)
    run_command(['systemctl', 'start', 'simple-bridge'], sudo=True, check=True)

    time.sleep(3)

    # Check status
    code, out, _ = run_command(['systemctl', 'status', 'simple-bridge'], check=False)
    if 'active (running)' in out:
        print_colored("✓ Simple bridge service is running.", Colors.GREEN)
    else:
        print_colored("Warning: Simple bridge service may not be running properly.", Colors.WARNING)


def check_bridge_health() -> bool:
    """Check if bridge is responding."""
    try:
        import requests
        response = requests.get("http://127.0.0.1:8789/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def launch_claude():
    """Launch the Claude TUI."""
    home = Path.home()
    claude_haha = home / "claude-code-haha" / "bin" / "claude-haha"

    if claude_haha.exists():
        os.execv(str(claude_haha), [str(claude_haha)])
    else:
        print_colored(f"Could not find claude-haha at {claude_haha}", Colors.FAIL)
        sys.exit(1)


def main():
    """Main wizard flow."""
    total_steps = 8

    # Print welcome banner
    print_colored("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║         Claude Code Setup Wizard                             ║
    ║         Installs and configures claude-code-haha             ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """, Colors.CYAN + Colors.BOLD)

    # STEP 1: Warn the user
    print_step(1, total_steps, "Safety Check")
    print_colored("⚠️  I am about to remove Claude Code from your machine.", Colors.WARNING + Colors.BOLD)
    print_colored("If you have any valuable work open or unsaved, please save it now before continuing.", Colors.WARNING)
    print()

    choice = prompt_user("What would you like to do?", [
        "I have valuable work — pause and let me save it",
        "I don't have valuable work — continue"
    ])

    if "have valuable work" in choice:
        print_colored("\nWizard paused. Please save your work and re-run this wizard when ready.", Colors.CYAN)
        print_colored("Command to re-run: python3 ~/claude-code-haha/setup_wizard.py", Colors.CYAN)
        sys.exit(0)

    # STEP 2: Python venv and wipe Claude
    print_step(2, total_steps, "Install Dependencies & Remove Existing Claude")
    install_dependencies()
    print()
    wipe_claude_installation()

    # STEP 3: Check for existing Keymaster
    print_step(3, total_steps, "Check for Existing Keymaster")
    keymaster_exists = check_keymaster_exists()
    has_auth, key_count = check_auth_profiles()

    skip_to_step_6 = False

    if keymaster_exists and has_auth:
        print_colored(f"Keymaster installation found with {key_count} API keys.", Colors.GREEN)

        # Check if service is running
        user = os.environ.get('USER', os.environ.get('USERNAME', 'root'))
        service_name = f"openclaw-keymaster@{user}"

        if is_systemd_service_active(service_name) or check_keymaster_health():
            print_colored("Keymaster is already running and healthy.", Colors.GREEN)
            skip_to_step_6 = True
        else:
            print_colored("Keymaster found but not running. Attempting to start...", Colors.WARNING)
            start_keymaster_service()
            if check_keymaster_health():
                print_colored("Keymaster is now running and healthy.", Colors.GREEN)
                skip_to_step_6 = True

    keys = []
    if not skip_to_step_6:
        # STEP 4: Clone Keymaster and collect keys
        print_step(4, total_steps, "Clone Keymaster & Collect API Keys")
        clone_keymaster()
        print()
        keys = collect_nvidia_keys()

        if len(keys) < 5:
            print_colored(f"\nWarning: You provided only {len(keys)} keys. 5 or more is recommended.", Colors.WARNING)
            if not confirm("Continue anyway?"):
                sys.exit(0)

        # STEP 4c: Write configurations
        print_step(4, total_steps, "Write Configuration Files")
        backup_openclaw_config()
        merge_openclaw_config(keys)
        write_auth_profiles(keys)

        # STEP 5: Install and start Keymaster
        print_step(5, total_steps, "Install & Start Keymaster")
        install_keymaster()
        start_keymaster_service()

        if not wait_for_keymaster_health(timeout=60):
            print_colored("\nKeymaster health check failed. Checking logs...", Colors.WARNING)
            run_command(['journalctl', '-u', f'openclaw-keymaster@{user}', '-n', '50'], sudo=True, capture=False)
            print_colored("\nPlease check the logs above and fix any issues before continuing.", Colors.FAIL)
            sys.exit(1)

        print_colored("✓ Keymaster is healthy and running on port 8787.", Colors.GREEN)

    # STEP 6: Install Chrome
    print_step(6, total_steps, "Install Chrome & Start Debug Port")
    chrome_binary = install_chrome()
    install_playwright()
    create_chrome_service(chrome_binary)

    # STEP 7: Start simple_bridge
    print_step(7, total_steps, "Start Simple Bridge Service")
    create_bridge_service()

    if check_bridge_health():
        print_colored("✓ Simple bridge is responding on port 8789.", Colors.GREEN)
    else:
        print_colored("Warning: Bridge may not be fully ready yet.", Colors.WARNING)

    # STEP 8: Final message and launch
    print_step(8, total_steps, "Complete & Launch Claude")

    print_colored("""
✅ Everything is set up!

Here's what's now running:

- Keymaster — API key rotation proxy on localhost:8787 with NVIDIA keys
- Chrome — Remote debug port open on 9222 (systemd-managed, always-on)
- simple_bridge.py — Running as a systemd service

Quick Keymaster commands:

- keymaster status — Current status
- keymaster health — Health check
- keymaster keys — List keys
- keymaster logs — Follow logs
- keymaster cooldowns — Show rate-limited keys
- keymaster reset — Clear all cooldowns

Starting Claude Code now...
""", Colors.GREEN + Colors.BOLD)

    time.sleep(2)
    launch_claude()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\nWizard interrupted. You can re-run with:", Colors.WARNING)
        print_colored("  python3 ~/claude-code-haha/setup_wizard.py", Colors.CYAN)
        sys.exit(0)
    except Exception as e:
        print_colored(f"\n\nError: {e}", Colors.FAIL)
        import traceback
        traceback.print_exc()
        sys.exit(1)
