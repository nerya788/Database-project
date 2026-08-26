"""Generic CRUD service: works off a TableSpec, not a specific table.

Table/column names come from our own trusted metadata (app/models/table_specs.py),
never from user input, so they are safely interpolated into SQL text; every
actual data value is still passed as a parameterized placeholder.
"""
from __future__ import annotations

from app.db.connection import Database
from app.models.table_specs import ColumnSpec, FKRef, TableSpec


class CrudService:
    @staticmethod
    def fetch_rows(spec: TableSpec) -> tuple[list[str], list[tuple]]:
        """Run the spec's human-readable list_query. Returns (column_labels, rows)."""
        with Database.cursor() as cur:
            cur.execute(spec.list_query)
            col_names = [d[0] for d in cur.description]
            rows = cur.fetchall()
        return col_names, rows

    @staticmethod
    def fetch_row_for_edit(spec: TableSpec, pk_values: dict) -> dict | None:
        """Raw (un-joined) row lookup by PK, used to pre-fill the edit form."""
        all_cols = [c.name for c in spec.columns]
        where = " AND ".join(f"{c} = %s" for c in spec.pk_columns)
        sql = f"SELECT {', '.join(all_cols)} FROM {spec.table} WHERE {where}"
        params = [pk_values[c] for c in spec.pk_columns]
        with Database.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        if row is None:
            return None
        return dict(zip(all_cols, row))

    @staticmethod
    def suggest_next_pk(spec: TableSpec):
        query = spec.suggest_pk_query()
        if query is None:
            return None
        with Database.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()[0]

    @staticmethod
    def fk_options(fk: FKRef) -> list[tuple]:
        """Returns [(id_value, label), ...] for a foreign-key combo box."""
        with Database.cursor() as cur:
            cur.execute(fk.query, fk.params)
            return cur.fetchall()

    @staticmethod
    def load_view_bundle(spec: TableSpec) -> dict:
        """Everything a freshly selected CRUD table needs, in one call: this
        lets the UI make a single background round trip (per-column FK
        options + the grid rows + a suggested next PK) instead of several
        separate synchronous ones, so switching tables never blocks the
        window's own event loop.
        """
        fk_options = {c.name: CrudService.fk_options(c.fk) for c in spec.columns if c.kind == "fk"}
        columns, rows = CrudService.fetch_rows(spec)
        suggested_pk = CrudService.suggest_next_pk(spec)
        return {
            "fk_options": fk_options,
            "columns": columns,
            "rows": rows,
            "suggested_pk": suggested_pk,
        }

    @staticmethod
    def insert(spec: TableSpec, values: dict) -> None:
        cols = spec.insert_columns
        col_names = [c.name for c in cols]
        placeholders = ", ".join(["%s"] * len(col_names))
        sql = f"INSERT INTO {spec.table} ({', '.join(col_names)}) VALUES ({placeholders})"
        params = [values.get(c.name) for c in cols]
        with Database.cursor() as cur:
            cur.execute(sql, params)

    @staticmethod
    def update(spec: TableSpec, pk_values: dict, values: dict) -> None:
        cols = spec.editable_columns
        set_clause = ", ".join(f"{c.name} = %s" for c in cols)
        where_clause = " AND ".join(f"{c} = %s" for c in spec.pk_columns)
        sql = f"UPDATE {spec.table} SET {set_clause} WHERE {where_clause}"
        params = [values.get(c.name) for c in cols] + [pk_values[c] for c in spec.pk_columns]
        with Database.cursor() as cur:
            cur.execute(sql, params)

    @staticmethod
    def delete(spec: TableSpec, pk_values: dict) -> None:
        where_clause = " AND ".join(f"{c} = %s" for c in spec.pk_columns)
        sql = f"DELETE FROM {spec.table} WHERE {where_clause}"
        params = [pk_values[c] for c in spec.pk_columns]
        with Database.cursor() as cur:
            cur.execute(sql, params)
