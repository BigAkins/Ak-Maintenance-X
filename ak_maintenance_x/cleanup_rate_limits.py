import time
from datetime import datetime, timezone

import requests

from ak_maintenance_x.cleanup_config import (
    AUTO_WAIT_ON_RATE_LIMIT_DEFAULT,
    RATE_LIMIT_RESET_BUFFER_SECONDS_DEFAULT,
)


def _safe_int(value):
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def get_rate_limit_info(response):
    headers = response.headers or {}

    return {
        "limit": _safe_int(headers.get("x-rate-limit-limit")),
        "remaining": _safe_int(headers.get("x-rate-limit-remaining")),
        "reset_epoch": _safe_int(headers.get("x-rate-limit-reset")),
    }


def format_reset_time(reset_epoch):
    if not reset_epoch:
        return "unknown reset time"

    dt = datetime.fromtimestamp(reset_epoch, tz=timezone.utc)
    return dt.isoformat()


def seconds_until_reset(
    reset_epoch,
    buffer_seconds=RATE_LIMIT_RESET_BUFFER_SECONDS_DEFAULT,
):
    if not reset_epoch:
        return buffer_seconds

    now = time.time()
    return max(0, int(reset_epoch - now + buffer_seconds))


def maybe_wait_from_success_response(
    response,
    action_label,
    auto_wait=AUTO_WAIT_ON_RATE_LIMIT_DEFAULT,
    buffer_seconds=RATE_LIMIT_RESET_BUFFER_SECONDS_DEFAULT,
):
    if not auto_wait:
        return False

    info = get_rate_limit_info(response)
    remaining = info["remaining"]
    reset_epoch = info["reset_epoch"]

    if remaining == 0:
        wait_seconds = seconds_until_reset(reset_epoch, buffer_seconds)
        print(
            f"[RATE LIMIT] {action_label}: remaining=0. "
            f"Waiting {wait_seconds}s until reset at {format_reset_time(reset_epoch)}."
        )
        time.sleep(wait_seconds)
        return True

    return False


def handle_rate_limit_http_error(
    error,
    action_label,
    auto_wait=AUTO_WAIT_ON_RATE_LIMIT_DEFAULT,
    buffer_seconds=RATE_LIMIT_RESET_BUFFER_SECONDS_DEFAULT,
):
    if not isinstance(error, requests.HTTPError):
        return False

    if error.response is None:
        return False

    if error.response.status_code != 429:
        return False

    if not auto_wait:
        print(f"[RATE LIMIT] {action_label}: hit 429 and auto-wait is disabled.")
        return False

    info = get_rate_limit_info(error.response)
    reset_epoch = info["reset_epoch"]
    wait_seconds = seconds_until_reset(reset_epoch, buffer_seconds)

    print(
        f"[RATE LIMIT] {action_label}: hit 429. "
        f"Waiting {wait_seconds}s until reset at {format_reset_time(reset_epoch)}."
    )
    time.sleep(wait_seconds)
    return True
