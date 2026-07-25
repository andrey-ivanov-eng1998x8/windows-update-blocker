import sys
import subprocess
import argparse
from pathlib import Path
import winreg
import ctypes

"""
Windows Update Blocker CLI.
Stop updates entirely by tackling services, registry keys, scheduled tasks, and DNS overrides.
"""

hostsPath = Path("C:/Windows/System32/drivers/etc/hosts")

BLOCK_DOMAINS = [
    "sls.update.microsoft.com",
    "fe2.update.microsoft.com",
    "fe3.delivery.mp.microsoft.com",
    "statsfe1.ws.microsoft.com",
    "statsfe2.ws.microsoft.com",
    "wu.delivery.mp.microsoft.com",
    "slscr.update.microsoft.com",
]

SCHEDULED_TASKS = [
    "\\Microsoft\\Windows\\WindowsUpdate\\Scheduled Start",
    "\\Microsoft\\Windows\\UpdateOrchestrator\\Schedule Scan",
    "\\Microsoft\\Windows\\UpdateOrchestrator\\Schedule Wake To Work",
    "\\Microsoft\\Windows\\UpdateOrchestrator\\UpdateModelTask",
    "\\Microsoft\\Windows\\UpdateOrchestrator\\USO_UxBroker",
]

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False

def run_cmd(args):
    # print(f"DEBUG: running command: {args}")
    res = subprocess.run(args, capture_output=True, text=True)
    return res.returncode == 0

def modify_services(stop=True):
    # UsoSvc can be protected on newer Win 11 builds, but stopping is still attempted
    # TODO: UsoSvc has a hardened DACL on newer Windows 11 builds, need to override permissions if sc config fails
    services = ["wuauserv", "bits", "UsoSvc", "waasmedsv"]
    for service in services:
        if stop:
            run_cmd(["sc", "config", service, "start=", "disabled"])
            run_cmd(["sc", "stop", service])
        else:
            # Restore back to manual launch trigger
            run_cmd(["sc", "config", service, "start=", "demand"])

def set_registry_policies(disable=True):
    reg_path = r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE)
        if disable:
            winreg.SetValueEx(key, "NoAutoUpdate", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "AUOptions", 0, winreg.REG_DWORD, 2)
        else:
            try:
                winreg.DeleteValue(key, "NoAutoUpdate")
                winreg.DeleteValue(key, "AUOptions")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except OSError as e:
        print(f"Warning: Could not modify registry keys: {e}")

def modify_tasks(disable=True):
    state = "/disable" if disable else "/enable"
    for task in SCHEDULED_TASKS:
        run_cmd(["schtasks", "/change", "/tn", task, state])

def update_hosts(block=True):
    if not hostsPath.exists():
        print("Error: Hosts file not found in System32 directory.")
        sys.exit(1)

    try:
        content = hostsPath.read_text(encoding="utf-8")
    except PermissionError:
        print("Error: Failed to read hosts file. Run terminal as Administrator.")
        sys.exit(1)

    lines = content.splitlines()
    # Strip out any legacy blocks first
    cleaned = [line for line in lines if not any(dom in line for dom in BLOCK_DOMAINS) 
               and "WINDOWS UPDATE BLOCKER" not in line]

    # Strip trailing whitespace lines to keep hosts clean
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()

    if block:
        cleaned.append("")
        cleaned.append("# BEGIN WINDOWS UPDATE BLOCKER")
        for dom in BLOCK_DOMAINS:
            cleaned.append(f"0.0.0.0 {dom}")
        cleaned.append("# END WINDOWS UPDATE BLOCKER")

    try:
        hostsPath.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
    except PermissionError:
        print("Error: Write permission denied on hosts file. Disable third-party AV if running as Admin.")
        sys.exit(1)

if __name__ == "__main__":
    if not is_admin():
        print("Error: Administrative privileges are required to modify system services, tasks, and hosts.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Completely freeze or restore automatic Windows updates.",
        epilog="Example: blocker.py --block"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--block", action="store_true", help="Disable and block Windows update mechanics.")
    group.add_argument("--restore", action="store_true", help="Restore default Windows update configuration.")
    
    args = parser.parse_args()

    if args.block:
        print("Stopping update services...")
        modify_services(stop=True)
        print("Writing registry policy keys...")
        set_registry_policies(disable=True)
        print("Disabling update tasks...")
        modify_tasks(disable=True)
        print("Adding domains to hosts file...")
        update_hosts(block=True)
        print("Windows Update is now fully blocked.")
    elif args.restore:
        print("Restoring update services...")
        modify_services(stop=False)
        print("Removing registry policy keys...")
        set_registry_policies(disable=False)
        print("Enabling system update tasks...")
        modify_tasks(disable=False)
        print("Cleaning up hosts file entries...")
        update_hosts(block=False)
        print("Windows Update restored back to defaults.")
