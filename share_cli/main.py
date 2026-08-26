"""share CLI — talks to the HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

from .walk import SecretFileError, walk_files

CONFIG_PATH = Path.home() / ".share" / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.is_file():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")
    CONFIG_PATH.chmod(0o600)


def _host(args) -> str:
    return (
        getattr(args, "host", None)
        or os.environ.get("SHARE_HOST")
        or load_config().get("host")
        or "http://localhost:8000"
    ).rstrip("/")


def _token(args) -> str:
    return (
        getattr(args, "token", None)
        or os.environ.get("SHARE_TOKEN")
        or load_config().get("token")
        or ""
    )


def _client(args) -> httpx.Client:
    token = _token(args)
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=_host(args), headers=headers, timeout=60.0)


def _die(resp: httpx.Response) -> None:
    try:
        err = resp.json().get("error") or {}
        msg = err.get("message") or resp.text
        code = err.get("code") or str(resp.status_code)
        print(f"error {code}: {msg}", file=sys.stderr)
    except Exception:
        print(f"error {resp.status_code}: {resp.text}", file=sys.stderr)
    sys.exit(1)


def cmd_whoami(args) -> None:
    with _client(args) as c:
        resp = c.get("/api/v1/me")
        if resp.status_code != 200:
            _die(resp)
        data = resp.json()
        if args.json:
            print(json.dumps(data))
            return
        print(data.get("handle") or data.get("id"))


def cmd_ls(args) -> None:
    params = {}
    if args.trash:
        params["trashed"] = "true"
    with _client(args) as c:
        resp = c.get("/api/v1/artifacts", params=params)
        if resp.status_code != 200:
            _die(resp)
        items = resp.json().get("items") or []
        if args.json:
            print(json.dumps(items))
            return
        for item in items:
            print(f"{item.get('name')}\t{item.get('kind')}\t{item.get('url', '')}")


def cmd_get(args) -> None:
    with _client(args) as c:
        resp = c.get(f"/api/v1/artifacts/{args.name}")
        if resp.status_code != 200:
            _die(resp)
        print(json.dumps(resp.json(), indent=2) if args.json else resp.json().get("url"))


def cmd_rm(args) -> None:
    with _client(args) as c:
        resp = c.delete(
            f"/api/v1/artifacts/{args.name}",
            params={"purge": "true"} if args.purge else None,
        )
        if resp.status_code not in {200, 204}:
            _die(resp)
        if not args.json:
            print("trashed" if not args.purge else "purged")


def cmd_restore(args) -> None:
    with _client(args) as c:
        resp = c.post(f"/api/v1/artifacts/{args.name}/restore")
        if resp.status_code != 200:
            _die(resp)
        if not args.json:
            print(resp.json().get("url"))


def cmd_post(args) -> None:
    root = Path(args.path)
    try:
        files = walk_files(root, force_secrets=args.force_secrets)
    except SecretFileError as exc:
        print(str(exc), file=sys.stderr)
        print("pass --force-secrets to override", file=sys.stderr)
        sys.exit(2)
    manifest = [
        {k: f[k] for k in ("path", "size", "contentType", "sha256")} for f in files
    ]
    body = {"files": manifest}
    if args.name:
        body["name"] = args.name
    if args.title:
        body["title"] = args.title
    if args.entry:
        body["entryPath"] = args.entry
    if args.note:
        body["note"] = args.note
    blobs = {f["sha256"]: f["bytes"] for f in files}
    if not args.json:
        print(f"Posting {root}  ({len(files)} files)")
    with _client(args) as c:
        declared = c.post("/api/v1/artifacts", json=body)
        if declared.status_code != 201:
            _die(declared)
        data = declared.json()
        for upload in data.get("uploads") or []:
            put = c.put(upload["url"], content=blobs[upload["sha256"]])
            if put.status_code != 200:
                _die(put)
        name = data["name"]
        committed = c.post(
            f"/api/v1/artifacts/{name}/versions/{data['versionId']}/commit"
        )
        if committed.status_code != 200:
            _die(committed)
        result = committed.json()
        if args.json:
            print(json.dumps(result))
            return
        print(f"Posted {result['name']} v{result['seq']} — {result['visibility']}")
        print()
        print(result["url"])


def cmd_login(args) -> None:
    host = _host(args)
    with httpx.Client(base_url=host, timeout=60.0) as c:
        started = c.post(
            "/api/v1/auth/device/start",
            json={"name": args.name or "share-cli"},
        )
        if started.status_code != 200:
            _die(started)
        data = started.json()
        print(f"Open {data['verifyUrl']} and enter {data['userCode']}")
        device = data["deviceCode"]
        deadline = time.time() + data.get("expiresIn", 600)
        interval = data.get("interval", 5)
        while time.time() < deadline:
            time.sleep(interval)
            polled = c.post("/api/v1/auth/device/poll", json={"deviceCode": device})
            if polled.status_code == 428:
                continue
            if polled.status_code != 200:
                _die(polled)
            token = polled.json()["token"]
            cfg = load_config()
            cfg["host"] = host
            cfg["token"] = token
            save_config(cfg)
            print("logged in")
            return
        print("login timed out", file=sys.stderr)
        sys.exit(1)


def cmd_logout(args) -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
    print("logged out")


def cmd_doctor(args) -> None:
    host = _host(args)
    with httpx.Client(base_url=host, timeout=5.0) as c:
        health = c.get("/health")
        ready = c.get("/internal/ready")
    print(f"host\t{host}")
    print(f"health\t{health.status_code}")
    print(f"ready\t{ready.status_code}")
    print(f"token\t{'yes' if _token(args) else 'no'}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="share")
    parser.add_argument("--host")
    parser.add_argument("--token")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("post")
    p.add_argument("path")
    p.add_argument("--name")
    p.add_argument("--title")
    p.add_argument("--entry")
    p.add_argument("--note")
    p.add_argument("--force-secrets", action="store_true")
    p.set_defaults(func=cmd_post)

    p = sub.add_parser("ls")
    p.add_argument("--trash", action="store_true")
    p.set_defaults(func=cmd_ls)

    p = sub.add_parser("get")
    p.add_argument("name")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("rm")
    p.add_argument("name")
    p.add_argument("--purge", action="store_true")
    p.set_defaults(func=cmd_rm)

    p = sub.add_parser("restore")
    p.add_argument("name")
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("whoami")
    p.set_defaults(func=cmd_whoami)

    p = sub.add_parser("login")
    p.add_argument("--name")
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("logout")
    p.set_defaults(func=cmd_logout)

    p = sub.add_parser("doctor")
    p.set_defaults(func=cmd_doctor)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
