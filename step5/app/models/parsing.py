"""Widget-string -> Python value coercion for CRUD form fields.

Kept separate from the UI layer so the same validation rules apply no
matter which widget rendered the field.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation


class ValidationError(ValueError):
    """Raised with a human-readable message safe to show in a dialog."""


def coerce(col, raw) -> object:
    """Convert a raw form value for `col` (a ColumnSpec) into a DB-ready value."""
    from app.models.table_specs import ColumnSpec  # local import: avoid cycle

    assert isinstance(col, ColumnSpec)

    if isinstance(raw, str):
        raw = raw.strip()

    is_blank = raw in ("", None)
    if is_blank:
        if col.nullable:
            return None
        raise ValidationError(f'"{col.label}" is required.')

    kind = col.kind
    try:
        if kind == "fk":
            # `raw` is already the native id value (int/str) resolved from the
            # FK combo box's option map - pass it through untouched so an
            # integer-typed FK column (e.g. school_id) isn't sent as text.
            return raw
        if kind in ("text", "enum"):
            return str(raw)
        if kind == "int":
            return int(str(raw))
        if kind == "decimal":
            return Decimal(str(raw))
        if kind == "bool":
            if isinstance(raw, bool):
                return raw
            return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")
        if kind == "date":
            return datetime.strptime(str(raw), "%Y-%m-%d").date()
        if kind == "time":
            return datetime.strptime(str(raw), "%H:%M").time()
        if kind == "datetime":
            return datetime.strptime(str(raw), "%Y-%m-%d %H:%M")
    except (ValueError, InvalidOperation) as exc:
        raise ValidationError(f'"{col.label}" has an invalid value: {exc}') from exc

    raise ValidationError(f"Unsupported field kind '{kind}' for {col.label}.")


def to_display(kind: str, value) -> str:
    """Format a raw DB value back into text for pre-filling a form field."""
    if value is None:
        return ""
    if isinstance(value, (date, datetime)) and kind == "date":
        return value.strftime("%Y-%m-%d")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, datetime) and kind == "datetime":
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)
