#!/usr/bin/env python3
"""Send one revision-safe command to the visible Blender sculpt session."""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent.parent
ROOT = PROJ / "tmp/tree_sculpt"
INBOX = ROOT / "inbox"
ACKS = ROOT / "acks"


def send(op, args, expected_revision, wait=15.0):
    INBOX.mkdir(parents=True, exist_ok=True)
    ACKS.mkdir(parents=True, exist_ok=True)
    command_id = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
    payload = {
        "id": command_id,
        "op": op,
        "args": args,
        "expected_revision": expected_revision,
    }
    temp = INBOX / f".{command_id}.tmp"
    final = INBOX / f"{command_id}.json"
    temp.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(temp, final)
    ack = ACKS / f"{command_id}.json"
    deadline = time.time() + wait
    while time.time() < deadline:
        if ack.exists():
            response = json.loads(ack.read_text())
            print(json.dumps(response, indent=2))
            return 0 if response.get("ok") else 1
        time.sleep(0.1)
    print(json.dumps({"ok": False, "error": f"timeout waiting for {ack}"}))
    return 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("op")
    parser.add_argument("--args", default="{}", help="JSON object")
    parser.add_argument("--revision", required=True, type=int)
    parser.add_argument("--wait", type=float, default=15.0)
    ns = parser.parse_args()
    args = json.loads(ns.args)
    if not isinstance(args, dict):
        parser.error("--args must decode to a JSON object")
    raise SystemExit(send(ns.op, args, ns.revision, ns.wait))


if __name__ == "__main__":
    main()

