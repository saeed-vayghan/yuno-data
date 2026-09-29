"""Slack adapter for the `Notifier` port (the one optional alert channel). Off by default:
alerts/run.py calls it only if alerts.yaml slack.enabled is true and the outbox has Slack lines;
it posts only if env SLACK_WEBHOOK_URL is set. Owner: ALERTS."""

import json
import os
import urllib.request

from casarecon.core import log

TIMEOUT_S = 5
MAX_CHARS = 3500  # Slack truncates long text blocks; the full report is in reports/alerts.md


def post(message: str) -> bool:
    """Post one message to SLACK_WEBHOOK_URL. True if sent; never raises (logs a warning)."""
    url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url.startswith("https://"):
        log.get("slack").info("slack skipped: SLACK_WEBHOOK_URL not set")
        return False
    body = json.dumps({"text": message[:MAX_CHARS]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310 (https only)
            return 200 <= resp.status < 300
    except Exception as e:  # network errors must never fail `recon alerts`
        log.get("slack").warning("slack post failed: %s", type(e).__name__)
        return False
