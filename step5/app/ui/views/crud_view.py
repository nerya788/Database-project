"""Generic, metadata-driven CRUD content pane for "Manage Data".

One CrudView instance serves every table registered in
app/models/table_specs.py: a form built on the fly from the selected
table's ColumnSpec list (with foreign keys rendered as label-dropdowns
that store the id in the background), and a searchable results grid below
it. Selecting a grid row auto-populates the form for editing ("Smart
Update Flow").

Which table is showing - and any category grouping - lives entirely in
the sidebar (app_window.py), which calls `select_table(spec)` on this
view. This view has no navigation UI of its own.
"""
from __future__ import annotations

import tkinter as tk
from typing import Optional

import customtkinter as ctk

from app.models.parsing import ValidationError, coerce, to_display
from app.models.table_specs import ColumnSpec, TableSpec
from app.services.crud_service import CrudService
from app.ui.async_utils import run_in_background
from app.ui.dialogs import confirm, show_db_error, show_error, show_info
from app.ui.theme import (
    ACCENT,
    ACCENT_HOVER,
    DANGER,
    SUCCESS,
    SURFACE,
    SURFACE_ALT,
    TEXT,
    TEXT_MUTED,
    WARNING,
    option_menu_style,
)
from app.ui.widgets.data_table import DataTable
from app.ui.widgets.fk_picker import FkPicker


class _FieldWidget:
    """Wraps one form input and knows how to get/set a typed value for it."""

    def __init__(self, master, column: ColumnSpec):
        self.column = column
        self._var: Optional[tk.Variable] = None

        if column.kind == "bool":
            self._var = tk.BooleanVar(value=False)
            self.widget = ctk.CTkCheckBox(master, text="", variable=self._var)
        elif column.kind == "enum":
            values = list(column.choices or [])
            if column.nullable:
                values = ["(none)"] + values
            self.widget = ctk.CTkOptionMenu(
                master, values=values or ["-"], fg_color=SURFACE_ALT,
                button_color=SURFACE_ALT, button_hover_color=ACCENT, **option_menu_style(),
            )
            if values:
                self.widget.set(values[0])
        elif column.kind == "fk":
            # FkPicker keeps the option list capped/search-filtered on screen
            # even for huge reference tables (e.g. 25k students) - a plain
            # CTkOptionMenu handed that many entries crashes Tk/Tcl outright.
            self.widget = FkPicker(master, nullable=column.nullable)
        else:
            placeholder = {
                "date": "YYYY-MM-DD",
                "time": "HH:MM",
                "datetime": "YYYY-MM-DD HH:MM",
            }.get(column.kind, "")
            self.widget = ctk.CTkEntry(master, placeholder_text=placeholder)

    def load_fk_options(self, options: list[tuple]) -> None:
        self.widget.set_options(options)

    def set_enabled(self, enabled: bool) -> None:
        if self.column.kind == "fk":
            self.widget.set_enabled(enabled)
            return
        state = "normal" if enabled else "disabled"
        try:
            self.widget.configure(state=state)
        except Exception:
            pass

    def clear(self) -> None:
        if self.column.kind == "bool":
            self._var.set(False)
        elif self.column.kind == "enum":
            values = list(self.column.choices or [])
            if self.column.nullable:
                values = ["(none)"] + values
            if values:
                self.widget.set(values[0])
        elif self.column.kind == "fk":
            self.widget.clear()
        else:
            self.widget.delete(0, "end")

    def set_value(self, raw_db_value) -> None:
        if self.column.kind == "bool":
            self._var.set(bool(raw_db_value))
        elif self.column.kind == "enum":
            self.widget.set("(none)" if raw_db_value is None else str(raw_db_value))
        elif self.column.kind == "fk":
            self.widget.set_selected(raw_db_value)
        else:
            self.widget.delete(0, "end")
            self.widget.insert(0, to_display(self.column.kind, raw_db_value))

    def get_raw(self):
        if self.column.kind == "bool":
            return self._var.get()
        if self.column.kind == "enum":
            value = self.widget.get()
            return None if value == "(none)" else value
        if self.column.kind == "fk":
            return self.widget.get_id()
        return self.widget.get()


class CrudView(ctk.CTkFrame):
    """A pure content pane - form + grid for whichever table it's told to
    show. It owns no navigation UI of its own: which table is active, and
    any category grouping, is entirely driven by the sidebar in
    app_window.py, which calls `select_table(spec)` directly.
    """

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._spec: Optional[TableSpec] = None
        self._fields: dict[str, _FieldWidget] = {}
        self._mode = "create"  # "create" | "edit"
        self._loaded_pk: Optional[dict] = None
        self._current_columns: list[str] = []
        # Value for the table's auto-assigned PK column (see
        # TableSpec.auto_assigned_pk_column) when creating a new record.
        # That column has no form widget - it is never shown to the user.
        self._pending_pk_value = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_main()

    def refresh_theme(self) -> None:
        self._table.refresh_theme()

    # -- Main: form card + data table -------------------------------------
    def _build_main(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self._form_card = ctk.CTkFrame(main, corner_radius=14, fg_color=SURFACE)
        self._form_card.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self._form_card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self._form_card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        self._title_label = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=18, weight="bold"),
                                          text_color=TEXT)
        self._title_label.pack(side="left")
        self._mode_badge = ctk.CTkLabel(header, text="NEW RECORD", text_color=SUCCESS,
                                         font=ctk.CTkFont(size=11, weight="bold"))
        self._mode_badge.pack(side="right")

        self._help_label = ctk.CTkLabel(self._form_card, text="", text_color=TEXT_MUTED, anchor="w")
        self._help_label.grid(row=1, column=0, sticky="ew", padx=20, pady=(2, 10))

        self._fields_frame = ctk.CTkScrollableFrame(self._form_card, height=220, fg_color="transparent")
        self._fields_frame.grid(row=2, column=0, sticky="ew", padx=20)
        self._fields_frame.grid_columnconfigure(1, weight=1)
        self._fields_frame.grid_columnconfigure(3, weight=1)

        btn_row = ctk.CTkFrame(self._form_card, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="ew", padx=20, pady=18)
        self._new_btn = ctk.CTkButton(btn_row, text="+ New", width=100, height=34, corner_radius=8,
                                       fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                       command=self._start_create)
        self._new_btn.pack(side="left", padx=(0, 8))
        self._save_btn = ctk.CTkButton(btn_row, text="Save", width=100, height=34, corner_radius=8,
                                        fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._save)
        self._save_btn.pack(side="left", padx=(0, 8))
        self._delete_btn = ctk.CTkButton(
            btn_row, text="Delete Selected", width=140, height=34, corner_radius=8,
            fg_color=DANGER, hover_color="#c93f43", command=self._delete,
        )
        self._delete_btn.pack(side="left", padx=(0, 8))
        self._refresh_btn = ctk.CTkButton(btn_row, text="Refresh", width=100, height=34,
                                           corner_radius=8, fg_color=SURFACE_ALT, text_color=TEXT,
                                           command=self._reload_table)
        self._refresh_btn.pack(side="right")

        self._table = DataTable(main, on_row_select=self._on_row_selected)
        self._table.grid(row=1, column=0, sticky="nsew")

    # -- Table selection ----------------------------------------------------
    def select_table(self, spec: TableSpec) -> None:
        """Switch the active table. Called by the sidebar in app_window.py
        whenever a table is clicked there - this view has no navigation UI
        of its own to keep in sync. All the DB work this implies (FK combo
        options, the grid rows, a suggested next PK) runs in the background
        - this method itself never blocks, so the window stays responsive
        (and, at startup, renders at all) no matter how slow/unreachable the
        database is.
        """
        self._spec = spec
        self._title_label.configure(text=spec.label)
        self._help_label.configure(
            text=spec.help_text or "Select a row below to edit it, or click + New to create one."
        )
        self._delete_btn.configure(state="disabled")
        self._new_btn.configure(state="disabled")
        self._save_btn.configure(state="disabled")

        self._build_form_skeleton()
        self._table.set_data([], [])
        self._set_busy(True, "Loading table data...")

        def work():
            return CrudService.load_view_bundle(spec)

        def on_done(bundle):
            if self._spec is not spec:
                return  # user switched tables again before this finished
            self._apply_bundle(spec, bundle)
            self._set_busy(False)

        def on_error(exc):
            if self._spec is not spec:
                return
            self._set_busy(False)
            show_db_error(exc, entity_label=spec.entity_name)

        run_in_background(self, work, on_done, on_error)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        state = "disabled" if busy else "normal"
        self._refresh_btn.configure(state=state)
        if busy:
            self._help_label.configure(text=message)
        else:
            spec = self._spec
            self._delete_btn.configure(state="disabled" if spec.readonly else "normal")
            self._new_btn.configure(state="disabled" if spec.readonly else "normal")
            self._help_label.configure(
                text=spec.help_text or "Select a row below to edit it, or click + New to create one."
            )

    def _apply_bundle(self, spec: TableSpec, bundle: dict) -> None:
        for name, options in bundle["fk_options"].items():
            if name in self._fields:
                self._fields[name].load_fk_options(options)

        self._current_columns = bundle["columns"]
        self._table.set_data(bundle["columns"], bundle["rows"], hidden_columns=spec.grid_hidden_columns)

        self._reset_form_to_create_mode()
        self._pending_pk_value = bundle["suggested_pk"]

    @staticmethod
    def _is_hidden_column(spec: TableSpec, column: ColumnSpec) -> bool:
        """True for PK columns with no form widget: database-generated
        (SERIAL) PKs, and single manually-sequential integer PKs (see
        TableSpec.auto_assigned_pk_column) that carry no business meaning a
        user should see or type.
        """
        return column.pk and (column.auto or column.name == spec.auto_assigned_pk_column)

    def _build_form_skeleton(self) -> None:
        """Build the form widgets only - no DB calls. FK combo boxes start
        showing "(loading...)" until `_apply_bundle` fills them in. Hidden
        PK columns (see `_is_hidden_column`) get no row at all.
        """
        for child in self._fields_frame.winfo_children():
            child.destroy()
        self._fields = {}

        row_index = 0
        for column in self._spec.columns:
            if self._is_hidden_column(self._spec, column):
                continue
            ctk.CTkLabel(self._fields_frame, text=column.label).grid(
                row=row_index, column=0, sticky="w", padx=(0, 8), pady=4
            )
            field = _FieldWidget(self._fields_frame, column)
            field.widget.grid(row=row_index, column=1, sticky="ew", pady=4)
            field.set_enabled(False)
            self._fields[column.name] = field
            row_index += 1

    # -- Create / Edit mode --------------------------------------------------
    def _reset_form_to_create_mode(self) -> None:
        """Synchronous, DB-free UI reset - used both right after a table's
        data bundle loads, and whenever the mode switches back to Create.
        """
        self._mode = "create"
        self._loaded_pk = None
        self._pending_pk_value = None
        self._mode_badge.configure(text="NEW RECORD", text_color=SUCCESS)
        self._table.clear_selection()
        self._save_btn.configure(state="disabled" if self._spec.readonly else "normal")

        for column in self._spec.columns:
            if self._is_hidden_column(self._spec, column):
                continue
            field = self._fields[column.name]
            field.clear()
            if column.auto:
                field.set_enabled(False)
            else:
                field.set_enabled(not self._spec.readonly)

    def _start_create(self) -> None:
        """"+ New" button handler: reset the form, then fetch a fresh
        suggested PK in the background (table contents may have changed
        since the last load). The PK itself is never shown - see
        `_pending_pk_value`.
        """
        spec = self._spec
        self._reset_form_to_create_mode()
        if spec.suggest_pk_query() is None:
            return

        def work():
            return CrudService.suggest_next_pk(spec)

        def on_done(value):
            if self._spec is not spec or self._mode != "create":
                return
            self._pending_pk_value = value

        def on_error(exc):
            if self._spec is spec:
                show_db_error(exc, entity_label=spec.entity_name)

        run_in_background(self, work, on_done, on_error)

    def _start_edit(self, pk_values: dict) -> None:
        spec = self._spec
        self._set_busy(True, "Loading record...")

        def work():
            return CrudService.fetch_row_for_edit(spec, pk_values)

        def on_done(row):
            if self._spec is not spec:
                return
            self._set_busy(False)
            if row is None:
                show_error("Not Found", "That record could not be reloaded (it may have been deleted).")
                self._reload_table()
                return
            self._apply_edit_row(spec, pk_values, row)

        def on_error(exc):
            if self._spec is not spec:
                return
            self._set_busy(False)
            show_db_error(exc, entity_label=spec.entity_name)

        run_in_background(self, work, on_done, on_error)

    def _apply_edit_row(self, spec: TableSpec, pk_values: dict, row: dict) -> None:
        self._mode = "edit"
        self._loaded_pk = pk_values
        self._mode_badge.configure(text="EDITING", text_color=WARNING)

        for column in spec.columns:
            if self._is_hidden_column(spec, column):
                continue
            field = self._fields[column.name]
            field.set_value(row.get(column.name))
            if column.pk or column.auto or spec.readonly:
                field.set_enabled(False)
            else:
                field.set_enabled(True)

        # Pure junction tables (e.g. Team_Players) have no non-PK columns, so
        # there is nothing to UPDATE for an existing row - only Delete applies.
        has_editable_fields = bool(spec.editable_columns)
        self._save_btn.configure(state="normal" if has_editable_fields else "disabled")

    def _on_row_selected(self, row: tuple) -> None:
        """`row` is always the full fetched record (every column the
        table's list_query returns, including any hidden-from-display PK/FK
        id columns) - DataTable tracks that separately from whatever subset
        is actually rendered, specifically so hiding a column from the grid
        can never break identifying which row was clicked.
        """
        if self._spec is None or self._spec.readonly:
            return
        try:
            pk_values = {
                pk_name: row[self._current_columns.index(pk_name)]
                for pk_name in self._spec.pk_columns
            }
        except ValueError:
            # A table's pk_columns must always be a subset of its
            # list_query output - this only fires if that invariant was
            # broken by a future edit, not from anything a user can trigger.
            show_error(
                "Selection Error",
                f"Could not identify the selected {self._spec.entity_name} record. "
                "Please refresh and try again.",
            )
            return
        self._start_edit(pk_values)

    # -- Data loading ---------------------------------------------------------
    def _reload_table(self) -> None:
        spec = self._spec
        self._set_busy(True, "Refreshing...")

        def work():
            return CrudService.fetch_rows(spec)

        def on_done(result):
            if self._spec is not spec:
                return
            self._set_busy(False)
            columns, rows = result
            self._current_columns = columns
            self._table.set_data(columns, rows, hidden_columns=spec.grid_hidden_columns)

        def on_error(exc):
            if self._spec is not spec:
                return
            self._set_busy(False)
            show_db_error(exc, entity_label=spec.entity_name)

        run_in_background(self, work, on_done, on_error)

    # -- Save / Delete ----------------------------------------------------------
    def _collect_values(self, columns: list[ColumnSpec]) -> dict:
        values = {}
        for column in columns:
            if column.name == self._spec.auto_assigned_pk_column:
                # No form widget exists for this column - it is never shown
                # to the user (see _is_hidden_column); its value came from
                # the background suggest_next_pk() fetch.
                values[column.name] = self._pending_pk_value
                continue
            raw = self._fields[column.name].get_raw()
            values[column.name] = coerce(column, raw)
        return values

    def _save(self) -> None:
        try:
            if self._mode == "create":
                if (self._spec.auto_assigned_pk_column is not None
                        and self._pending_pk_value is None):
                    raise ValidationError(
                        "Still preparing this record's internal ID - please try Save again "
                        "in a moment."
                    )
                values = self._collect_values(self._spec.insert_columns)
                CrudService.insert(self._spec, values)
                show_info("Success", f"{self._spec.label}: record created.")
            else:
                values = self._collect_values(self._spec.editable_columns)
                CrudService.update(self._spec, self._loaded_pk, values)
                show_info("Success", f"{self._spec.label}: record updated.")
        except ValidationError as exc:
            show_error("Invalid Input", str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - psycopg2 errors land here
            show_db_error(exc, entity_label=self._spec.entity_name)
            return

        self._reload_table()
        self._start_create()

    def _delete(self) -> None:
        if self._mode != "edit" or self._loaded_pk is None:
            show_error("No Selection", "Select a row in the table first.")
            return
        if not confirm("Confirm Delete", f"Permanently delete this {self._spec.entity_name}?"):
            return
        try:
            CrudService.delete(self._spec, self._loaded_pk)
        except Exception as exc:  # noqa: BLE001
            show_db_error(exc, entity_label=self._spec.entity_name)
            return
        show_info("Deleted", f"{self._spec.label}: record deleted.")
        self._reload_table()
        self._start_create()
