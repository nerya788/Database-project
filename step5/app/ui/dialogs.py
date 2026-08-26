"""Modal alert / confirm / toast helpers used across every screen.

`show_db_error` is the single entry point every DB-facing error handler in
the app should use: it turns a raw psycopg2 exception into a clean,
user-facing dialog (title + plain-language message + a short next-step
hint) and never puts SQL text, constraint names, or internal ids in front
of the user. The full technical exception is always logged instead, for
whoever needs to diagnose the issue from the console/log file.
"""
from __future__ import annotations

import logging
import re
import tkinter.messagebox as messagebox
from typing import Optional

from app.config import APP_NAME

logger = logging.getLogger("app.db_errors")

# PostgreSQL SQLSTATE codes (stable across server locales - the reliable way
# to branch on error *kind*; message text is only used for the extra detail
# a code alone doesn't carry, e.g. which table/column was involved).
_SQLSTATE_RESTRICT = "23001"   # DELETE/UPDATE blocked: another table still refers to this row
_SQLSTATE_FK = "23503"         # INSERT/UPDATE refers to a row that doesn't exist
_SQLSTATE_UNIQUE = "23505"
_SQLSTATE_CHECK = "23514"
_SQLSTATE_NOT_NULL = "23502"

_NOT_PRESENT_RE = re.compile(r'is not present in table "(\w+)"')
_UNIQUE_KEY_RE = re.compile(r"^Key \(([\w, ]+)\)=")


def show_error(title: str, message: str) -> None:
    messagebox.showerror(f"{APP_NAME} - {title}", message)


def show_info(title: str, message: str) -> None:
    messagebox.showinfo(f"{APP_NAME} - {title}", message)


def show_warning(title: str, message: str) -> None:
    messagebox.showwarning(f"{APP_NAME} - {title}", message)


def confirm(title: str, message: str) -> bool:
    return messagebox.askyesno(f"{APP_NAME} - {title}", message)


def _friendly_table_name(raw_table_name: Optional[str]) -> str:
    """Raw Postgres table name (as returned in diag/DETAIL text) -> the
    same prose-friendly name used elsewhere in the app for that table."""
    if not raw_table_name:
        return "other records"
    from app.models.table_specs import TABLE_SPECS  # local import: avoid any import-order issue

    for spec in TABLE_SPECS.values():
        if spec.table.lower() == raw_table_name.lower():
            return spec.entity_name
    return raw_table_name.replace("_", " ").title()


def _friendly_field_name(raw_column_name: Optional[str]) -> str:
    """"captain_student_id" -> "Captain Student ID"; "col_a, col_b" (a
    composite constraint) -> "Col A and Col B"."""
    if not raw_column_name:
        return "This field"
    columns = [c.strip() for c in raw_column_name.split(",") if c.strip()]
    return " and ".join(
        " ".join(w.upper() if w.lower() == "id" else w.capitalize() for w in col.split("_"))
        for col in columns
    )


def _pluralize(name: str) -> str:
    """Simple English pluralizer, sufficient for the entity_name values
    defined in table_specs.py (e.g. "Student" -> "Students", "Roster Entry"
    -> "Roster Entries", "Match" -> "Matches")."""
    if name.endswith(("s", "x", "z")) or name.endswith(("ch", "sh")):
        return name + "es"
    if len(name) >= 2 and name[-1] == "y" and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    return name + "s"


def humanize_db_error(exc: Exception, entity_label: Optional[str] = None) -> tuple[str, str]:
    """Turn a psycopg2 error into a (title, message) pair safe to show a
    user. `entity_label` is the prose name of the record being acted on
    (e.g. "School") when the caller knows it - it sharpens phrasing like
    "This School cannot be deleted...".
    """
    logger.warning("Database error while handling a user action: %s", exc, exc_info=True)

    pgcode = getattr(exc, "pgcode", None)
    diag = getattr(exc, "diag", None)
    subject = entity_label or "record"

    if pgcode == _SQLSTATE_RESTRICT and diag is not None:
        blocker = _pluralize(_friendly_table_name(diag.table_name))
        return (
            "Cannot Delete Record",
            f"This {subject} cannot be deleted because it currently has "
            f"associated {blocker} linked to it.\n\n"
            "Please reassign or delete the associated records first.",
        )

    if pgcode == _SQLSTATE_FK and diag is not None:
        detail = diag.message_detail or ""
        match = _NOT_PRESENT_RE.search(detail)
        missing = _friendly_table_name(match.group(1)) if match else None
        subject_phrase = f"a {missing}" if missing else "the selected value"
        return (
            "Invalid Selection",
            f"This action refers to {subject_phrase} that no longer exists.\n\n"
            "Please refresh this screen and try again.",
        )

    if pgcode == _SQLSTATE_UNIQUE and diag is not None:
        detail = diag.message_detail or ""
        match = _UNIQUE_KEY_RE.search(detail)
        field = _friendly_field_name(match.group(1)) if match else None
        if field:
            return (
                "Duplicate Value",
                f'"{field}" must be unique, and that value is already used by another '
                f"{subject}.\n\nPlease choose a different value and try again.",
            )
        return (
            "Duplicate Value",
            f"That value is already used by another {subject}.\n\n"
            "Please choose a different value and try again.",
        )

    if pgcode == _SQLSTATE_CHECK and diag is not None:
        return (
            "Invalid Value",
            "One of the entered values is outside the allowed range for this field.\n\n"
            "Please review your entry and try again.",
        )

    if pgcode == _SQLSTATE_NOT_NULL and diag is not None:
        field = _friendly_field_name(diag.column_name)
        return (
            "Missing Information",
            f'"{field}" is required and cannot be left empty.',
        )

    return (
        "Something Went Wrong",
        "The database could not complete this action. Please try again, and if the "
        "problem continues, contact your system administrator.",
    )


def show_db_error(exc: Exception, entity_label: Optional[str] = None) -> None:
    """Log the real exception, then show the user only the friendly version."""
    title, message = humanize_db_error(exc, entity_label)
    show_error(title, message)


def connection_error_message(exc: Exception) -> str:
    """Short, one-line explanation for a failed connection attempt - used by
    the dashboard's status indicator, which shows inline text rather than a
    dialog. Still never surfaces the raw driver/SQL text; the real exception
    is logged instead.
    """
    logger.warning("Database connection check failed: %s", exc, exc_info=True)
    text = (str(exc).strip().splitlines() or [""])[0].lower()

    if "password" in text or "authentication" in text:
        return "Authentication failed - check the database credentials in .env."
    if "does not exist" in text and "database" in text:
        return "The configured database does not exist."
    if any(s in text for s in ("could not connect", "connection refused", "timeout", "timed out")):
        return "Could not reach the database server - check the host and port, and that it is running."
    return "Unable to connect to the database."
