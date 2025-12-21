"""System setup helpers for bootstrap and re-opening setup."""

import os

from app import models

SETUP_COMPLETE_KEY = "setup_complete"
SETUP_REOPENED_KEY = "setup_reopened"


def _get_setting(db, key: str) -> models.SystemSetting | None:
    return db.get(models.SystemSetting, key)


def _set_setting(db, key: str, value: str) -> None:
    setting = _get_setting(db, key)
    if setting:
        setting.value = value
    else:
        db.add(models.SystemSetting(key=key, value=value))


def ensure_setup_state(db) -> None:
    """Ensure setup flags exist; seed defaults based on current data."""
    setup_complete = _get_setting(db, SETUP_COMPLETE_KEY)
    setup_reopened = _get_setting(db, SETUP_REOPENED_KEY)

    if setup_complete is None:
        has_users = db.query(models.User).count() > 0
        _set_setting(db, SETUP_COMPLETE_KEY, "true" if has_users else "false")

    if setup_reopened is None:
        _set_setting(db, SETUP_REOPENED_KEY, "false")

    db.commit()


def get_setup_status(db) -> tuple[bool, bool]:
    ensure_setup_state(db)
    setup_complete = _get_setting(db, SETUP_COMPLETE_KEY)
    setup_reopened = _get_setting(db, SETUP_REOPENED_KEY)
    return (
        setup_complete.value.lower() == "true",
        setup_reopened.value.lower() == "true",
    )


def set_setup_status(db, complete: bool, reopened: bool) -> None:
    _set_setting(db, SETUP_COMPLETE_KEY, "true" if complete else "false")
    _set_setting(db, SETUP_REOPENED_KEY, "true" if reopened else "false")
    db.commit()


def mark_setup_complete(db) -> None:
    set_setup_status(db, True, False)


def mark_setup_reopened(db) -> None:
    set_setup_status(db, False, True)


def validate_reopen_token(token: str | None) -> tuple[bool, str | None]:
    expected = os.getenv("SETUP_REOPEN_TOKEN")
    if not expected:
        return False, "Setup reopen token is not configured."
    if not token:
        return False, "Setup reopen token is required."
    if token != expected:
        return False, "Invalid setup reopen token."
    return True, None
