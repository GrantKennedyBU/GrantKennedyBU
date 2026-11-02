"""Excerpt: the AI Ops Agent's tamper-evident audit log.

From the root broker in a private repository (ai/broker/broker.py),
shared here as a sample. Every action the agent
requests is written as one JSON event. Each event stores the hash of the
event before it, so changing or deleting any past event breaks the chain.
Each new hash is also copied into the systemd journal as an independent
record that a separate verify tool checks against.

Shown as written, apart from the imports and constants gathered at the top.
"""

import fcntl
import hashlib
import json
import logging
import os
import re
import socket
import stat
from datetime import datetime, timezone
from pathlib import Path

AUDIT_ROOT = Path("/var/log/aiops/cases")
CASE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")

# ---- Phase 4B: tamper-evident chaining -------------------------------------
# Each event carries seq, prev_hash and hash = sha256(prev_hash + canonical
# event). The first chained event in a file that already holds older,
# unchained events uses the sha256 of that existing content as prev_hash.
# Every hash is also anchored in the systemd journal (independent store).

GENESIS = "0" * 64
JOURNAL_SOCKET = "/run/systemd/journal/socket"


def canonical(event: dict) -> bytes:
    body = {k: v for k, v in event.items() if k != "hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def chain_hash(prev_hash: str, event: dict) -> str:
    return hashlib.sha256(prev_hash.encode("ascii") + canonical(event)).hexdigest()


def _chain_tail(log_fd: int) -> tuple:
    """Return (last_seq, last_hash) for the open log."""
    size = os.fstat(log_fd).st_size
    if size == 0:
        return 0, GENESIS
    window = os.pread(log_fd, min(size, 262144), max(0, size - 262144))
    for line in reversed(window.splitlines()):
        if line.strip():
            try:
                last = json.loads(line)
            except ValueError:
                break
            if "hash" in last and "seq" in last:
                return last["seq"], last["hash"]
            break
    # Legacy (unchained) content: anchor the whole existing file.
    digest, offset = hashlib.sha256(), 0
    while offset < size:
        block = os.pread(log_fd, 1 << 20, offset)
        digest.update(block)
        offset += len(block)
    return 0, "legacy:" + digest.hexdigest()


def _anchor(case_id: str, event: dict) -> None:
    """Best-effort copy of the chain head into the journal."""
    payload = "\n".join([
        f"MESSAGE=aiops audit {case_id} seq={event['seq']} {event['hash']}",
        "SYSLOG_IDENTIFIER=aiops-audit", "PRIORITY=6",
        f"AIOPS_CASE={case_id}", f"AIOPS_SEQ={event['seq']}",
        f"AIOPS_HASH={event['hash']}"]) + "\n"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.sendto(payload.encode("utf-8"), JOURNAL_SOCKET)
    except OSError:
        logging.warning("audit anchor for %s seq %s not written",
                        case_id, event["seq"])


def audit(case_id: str, record: dict) -> None:
    """Write a durable, hash-chained event through verified descriptors."""
    if not CASE_RE.fullmatch(case_id):
        raise ValueError("Invalid case ID")

    event = dict(record)
    event["timestamp"] = datetime.now(timezone.utc).isoformat()

    directory_flags = (
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )

    root_fd = os.open(AUDIT_ROOT, directory_flags)
    try:
        root_info = os.fstat(root_fd)
        if (
            root_info.st_uid != os.geteuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
        ):
            raise PermissionError("Unsafe audit root")

        try:
            os.mkdir(case_id, mode=0o700, dir_fd=root_fd)
            os.fsync(root_fd)
        except FileExistsError:
            pass

        case_fd = os.open(case_id, directory_flags, dir_fd=root_fd)
        try:
            case_info = os.fstat(case_fd)
            if (
                case_info.st_uid != os.geteuid()
                or stat.S_IMODE(case_info.st_mode) != 0o700
            ):
                raise PermissionError("Unsafe case directory")

            flags = (
                os.O_RDWR | os.O_CREAT | os.O_APPEND
                | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            )
            log_fd = os.open(
                "events.jsonl", flags, 0o600, dir_fd=case_fd
            )
            try:
                info = os.fstat(log_fd)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) != 0o600
                ):
                    raise PermissionError("Unsafe audit log")

                fcntl.flock(log_fd, fcntl.LOCK_EX)
                seq, prev_hash = _chain_tail(log_fd)
                event["seq"] = seq + 1
                event["prev_hash"] = prev_hash
                event["hash"] = chain_hash(prev_hash, event)
                data = (json.dumps(event, sort_keys=True) + "\n").encode("utf-8")
                written = os.write(log_fd, data)
                if written != len(data):
                    raise OSError("Incomplete audit write")

                os.fsync(log_fd)
                os.fsync(case_fd)
            finally:
                os.close(log_fd)   # also releases the lock
            _anchor(case_id, event)
        finally:
            os.close(case_fd)
    finally:
        os.close(root_fd)

