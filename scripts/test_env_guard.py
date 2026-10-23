#!/usr/bin/env python3
"""Test-environment guard: results only count if they ran on Bradley's laptop.

Every validation run (FreeCAD checks, parameter sweeps, audit) must call
require_laptop() first and print the banner it returns. If the run is not on
the enrolled machine -- a cloud VM, a sandbox, a headless FreeCAD, a second
FreeCAD install -- it raises InvalidTestEnvironment and nothing may be
reported as passing.

The expected fingerprint lives OUTSIDE every repo, at
~/.config/cornercad/test_machine.json, so a sandbox checkout never has it.
Only Bradley creates it, from his own Terminal:

    python3 test_env_guard.py --enroll

Enrollment refuses to run without an interactive terminal, so an agent's
Bash tool cannot enroll a machine. There is deliberately no bypass flag.

Usage inside FreeCAD (MCP execute_python or a macro):

    import sys, importlib
    sys.path.insert(0, "<project>/scripts")
    import test_env_guard; importlib.reload(test_env_guard)
    print(test_env_guard.require_laptop(need_freecad=True))

Usage from a plain Python script:

    from test_env_guard import require_laptop
    print(require_laptop(need_freecad=False))

CLI check (exit 0 = verified, 2 = invalid):

    python3 test_env_guard.py
"""

import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime

ENROLL_PATH = os.path.expanduser("~/.config/cornercad/test_machine.json")
MCP_ADDON = "freecad-addon-robust-mcp-server"


class InvalidTestEnvironment(RuntimeError):
    """Raised when tests are not running on the enrolled laptop."""


def _hardware_uuid():
    if platform.system() != "Darwin":
        return None
    try:
        out = subprocess.run(
            ["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in out.splitlines():
        if "IOPlatformUUID" in line:
            return line.split('"')[3]
    return None


def _freecad_info():
    """FreeCAD facts if running inside FreeCAD, else None."""
    fc = sys.modules.get("FreeCAD")
    if fc is None:
        return None
    return {
        "home": os.path.normpath(fc.getHomePath()),
        "user_dir": os.path.normpath(fc.getUserAppDataDir()),
        "version": ".".join(fc.Version()[:3]),
        "gui": bool(fc.GuiUp),
    }


def fingerprint():
    return {
        "hardware_uuid": _hardware_uuid(),
        "hostname": socket.gethostname(),
        "system": platform.system(),
        "arch": platform.machine(),
        "freecad": _freecad_info(),
    }


def _load_enrollment():
    try:
        with open(ENROLL_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _banner(ok, fp, problems=(), warnings=()):
    uuid = (fp["hardware_uuid"] or "none")[:8]
    fc = fp["freecad"]
    fc_desc = "no FreeCAD" if fc is None else (
        f"FreeCAD {fc['version']} {'GUI' if fc['gui'] else 'HEADLESS'}")
    lines = []
    if ok:
        lines.append(f"TEST ENVIRONMENT VERIFIED: {fp['hostname']} "
                     f"uuid {uuid} {fc_desc}")
    else:
        lines.append("=" * 64)
        lines.append("INVALID TEST ENVIRONMENT -- RESULTS DO NOT COUNT")
        lines.append(f"host {fp['hostname']} uuid {uuid} {fc_desc}")
        lines += [f"  - {p}" for p in problems]
        lines.append("Stop. Report this to Bradley; do not report any test "
                     "as passing.")
        lines.append("=" * 64)
    lines += [f"  warning: {w}" for w in warnings]
    return "\n".join(lines)


def require_laptop(need_freecad=True):
    """Return a VERIFIED banner, or raise InvalidTestEnvironment."""
    fp = fingerprint()
    enrolled = _load_enrollment()
    problems, warnings = [], []

    if enrolled is None:
        problems.append(f"no enrollment file at {ENROLL_PATH} "
                        "(this is not the enrolled laptop)")
    else:
        if fp["hardware_uuid"] is None:
            problems.append("cannot read a macOS hardware UUID "
                            "(not a Mac, or a VM/sandbox)")
        elif fp["hardware_uuid"] != enrolled["hardware_uuid"]:
            problems.append("hardware UUID does not match the enrolled "
                            "laptop")

    fc = fp["freecad"]
    if need_freecad:
        if fc is None:
            problems.append("not running inside FreeCAD")
        else:
            if not fc["gui"]:
                problems.append("FreeCAD is headless; tests must run in "
                                "the GUI FreeCAD the MCP bridge drives")
            if enrolled is not None:
                if fc["home"] != enrolled["freecad_home"]:
                    problems.append(f"FreeCAD install {fc['home']} is not "
                                    f"the enrolled {enrolled['freecad_home']}")
                if fc["version"] != enrolled["freecad_version"]:
                    warnings.append(
                        f"FreeCAD {fc['version']} differs from enrolled "
                        f"{enrolled['freecad_version']}; re-enroll if this "
                        "update was intentional")
            if not os.path.isdir(os.path.join(fc["user_dir"], "Mod",
                                              MCP_ADDON)):
                problems.append(f"{MCP_ADDON} addon not installed in this "
                                "FreeCAD")

    if problems:
        raise InvalidTestEnvironment(_banner(False, fp, problems, warnings))
    return _banner(True, fp, warnings=warnings)


def _enroll():
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        sys.exit("Enrollment needs an interactive terminal. Run it yourself "
                 "in Terminal.app, not through an agent.")
    fp = fingerprint()
    if fp["hardware_uuid"] is None:
        sys.exit("No macOS hardware UUID found; refusing to enroll.")
    home = "/Applications/FreeCAD.app/Contents/Resources"
    record = {
        "hardware_uuid": fp["hardware_uuid"],
        "hostname": fp["hostname"],
        "freecad_home": home,
        "freecad_version": input("FreeCAD version as shown in "
                                 "Help > About (e.g. 1.1.4): ").strip(),
        "enrolled_at": datetime.now().isoformat(timespec="seconds"),
    }
    print(json.dumps(record, indent=2))
    if input(f"Write this to {ENROLL_PATH}? [y/N] ").strip().lower() != "y":
        sys.exit("Not enrolled.")
    os.makedirs(os.path.dirname(ENROLL_PATH), exist_ok=True)
    with open(ENROLL_PATH, "w") as f:
        json.dump(record, f, indent=2)
    print("Enrolled.")


if __name__ == "__main__":
    if "--enroll" in sys.argv[1:]:
        _enroll()
        sys.exit(0)
    try:
        print(require_laptop(need_freecad=False))
    except InvalidTestEnvironment as e:
        print(e)
        sys.exit(2)
