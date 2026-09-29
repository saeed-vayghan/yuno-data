"""Kept for `core.deps.get_notifier()`: the Slack adapter now lives in notify_slack.py. Owner: ALERTS."""

from casarecon.adapters.notify_slack import MAX_CHARS, TIMEOUT_S, post

__all__ = ["MAX_CHARS", "TIMEOUT_S", "post"]
