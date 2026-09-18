# windows-update-blocker

I got tired of Windows waking up my laptop in my backpack at 3 AM, running updates that break my WSL environment and docker mounts, and leaving my fans spinning. This is a single-script hammer to stop Windows from updating itself.

It requires Administrator privileges to run, as it modifies system services, tasks, registry keys, and the hosts file.

## How it works

The script performs four layers of blocking:
1. **Services**: Force-stops and disables `wuauserv` (Windows Update), `UsoSvc` (Update Orchestrator), and `WaaSMedicSvc` (Windows Update Medic).
2. **Registry**: Writes system policies to disable automatic updates and user access to the update interface.
3. **Scheduled Tasks**: Disables the built-in update scan and reboot tasks that Windows silently recreates.
4. **Hosts File**: Adds entries pointing common Microsoft update and telemetry servers to `127.0.0.1` as a final fallback.

## Installation

No installation or external packages required. Just clone or download the script and run it with Python 3 on Windows.

## Usage

Open an elevated Command Prompt or PowerShell (Run as Administrator) and run:

```cmd
python blocker.py status
```

To disable all updates:

```cmd
python blocker.py block
```

To restore default Windows Update settings:

```cmd
python blocker.py unblock
```

Command line help:

```cmd
python blocker.py --help
```

<!-- last-checked: 2026-09-18 -->
