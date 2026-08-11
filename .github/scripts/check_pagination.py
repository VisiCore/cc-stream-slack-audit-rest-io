#!/usr/bin/env python3
"""Confirm cursor pagination advances against the live Audit Logs API.

The collector pages by sending a `cursor` request parameter built from
`response_metadata.next_cursor`. This asks for one entry per page and checks
that following the cursor returns a *different* entry, which is the behaviour
a missing or misnamed cursor parameter silently breaks.

Skips (exit 0) when no token is configured, so the job stays green on any
checkout that has not opted in. Only stdlib is used, so the job needs no
dependency install step.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import NoReturn

API_URL = os.environ.get("SLACK_AUDIT_API_URL", "https://api.slack.com/audit/v1/logs")
TOKEN = os.environ.get("SLACK_AUDIT_TOKEN", "").strip()
TIMEOUT = 30


def fetch(cursor: str | None) -> dict:
    """Request a single-entry page, optionally continuing from a cursor."""
    params = {"limit": "1"}
    if cursor:
        params["cursor"] = cursor
    request = urllib.request.Request(
        f"{API_URL}?{urllib.parse.urlencode(params)}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read())


def fail(message: str) -> NoReturn:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    if not TOKEN:
        print("SKIP: no token configured; pagination check not run.")
        return

    try:
        first = fetch(None)
    except urllib.error.HTTPError as exc:
        # The body can echo request details; report only the status.
        fail(f"first page request returned HTTP {exc.code}")
    except urllib.error.URLError as exc:
        fail(f"first page request failed: {exc.reason}")

    if not first.get("ok", True):
        fail(f"API reported an error: {first.get('error', 'unknown')}")

    entries = first.get("entries") or []
    if not entries:
        print("SKIP: no audit entries available to paginate.")
        return

    cursor = (first.get("response_metadata") or {}).get("next_cursor") or ""
    if not cursor:
        print("SKIP: only one page of entries available; nothing to advance to.")
        return

    try:
        second = fetch(cursor)
    except urllib.error.HTTPError as exc:
        fail(f"cursor was rejected with HTTP {exc.code}")
    except urllib.error.URLError as exc:
        fail(f"second page request failed: {exc.reason}")

    second_entries = second.get("entries") or []
    if not second_entries:
        fail("following the cursor returned no entries")

    first_id = entries[0].get("id")
    second_id = second_entries[0].get("id")
    if first_id == second_id:
        fail("following the cursor returned the same entry; pagination did not advance")

    print("PASS: cursor pagination advanced to a distinct entry.")


if __name__ == "__main__":
    main()
