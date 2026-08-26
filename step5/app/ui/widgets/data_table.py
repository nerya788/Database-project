"""Reusable, searchable data grid: a search bar + a themed ttk.Treeview with
theme-aware alternating row colors, content-based column auto-sizing, and
support for columns that are fetched (needed to identify the selected row)
but never rendered - e.g. a raw foreign-key id standing behind its resolved,
human-readable label column.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from typing import Callable, Optional

import customtkinter as ctk

from app.ui.theme import SURFACE, TEXT_MUTED, row_stripe_colors, style_treeview

_MIN_COL_WIDTH = 90
_MAX_COL_WIDTH = 340
_CHAR_PX = 7  # rough average glyph width for the grid's font, in pixels


class DataTable(ctk.CTkFrame):
    def __init__(self, master, on_row_select: Optional[Callable[[tuple], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_row_select = on_row_select
        self._all_rows: list[tuple] = []
        self._columns: list[str] = []          # every fetched column (data model)
        self._display_columns: list[str] = []  # subset actually rendered, in order
        self._display_indices: list[int] = []  # self._columns index for each display column
        self._build()

    def _build(self) -> None:
        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(search_bar, text="\U0001F50D", font=ctk.CTkFont(size=14)).pack(
            side="left", padx=(2, 6)
        )
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        entry = ctk.CTkEntry(search_bar, textvariable=self._search_var,
                              placeholder_text="Search this list...", width=300, height=34,
                              corner_radius=8)
        entry.pack(side="left")

        self._count_label = ctk.CTkLabel(search_bar, text="", text_color=TEXT_MUTED)
        self._count_label.pack(side="right")

        table_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=12)
        table_frame.pack(fill="both", expand=True)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        style_treeview()
        self._tree = ttk.Treeview(table_frame, show="headings", style="App.Treeview", selectmode="browse")
        self._tree.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=(1, 0))

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        vsb.grid(row=0, column=1, sticky="ns", pady=(1, 0))
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self._tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._apply_stripe_colors()
        self._tree.bind("<<TreeviewSelect>>", self._handle_select)

    def _apply_stripe_colors(self) -> None:
        even_bg, odd_bg = row_stripe_colors()
        self._tree.tag_configure("even", background=even_bg)
        self._tree.tag_configure("odd", background=odd_bg)

    def refresh_theme(self) -> None:
        style_treeview()
        self._apply_stripe_colors()
        if self._all_rows:
            self._render(self._current_visible_rows())

    def set_data(self, columns: list[str], rows: list[tuple],
                 hidden_columns: Optional[list[str]] = None) -> None:
        """`columns`/`rows` are the full query result (used to identify the
        selected row). `hidden_columns` names columns to keep in that data
        but exclude from the rendered grid.
        """
        self._columns = columns
        self._all_rows = rows

        hidden = set(hidden_columns or [])
        self._display_columns = [c for c in columns if c not in hidden]
        self._display_indices = [columns.index(c) for c in self._display_columns]

        self._tree.configure(columns=self._display_columns)
        for col in self._display_columns:
            self._tree.heading(col, text=col.replace("_", " ").title())
        self._autosize_columns(rows)
        self._render(rows)

    def _autosize_columns(self, rows: list[tuple]) -> None:
        """Size each visible column to fit its longest value (header included)
        instead of a fixed width, so full names/dates/phone numbers aren't
        clipped.
        """
        for col, idx in zip(self._display_columns, self._display_indices):
            longest = len(col.replace("_", " ").title())
            for row in rows:
                value = row[idx]
                if value is not None:
                    value_len = len(str(value))
                    if value_len > longest:
                        longest = value_len
            width = max(_MIN_COL_WIDTH, min(_MAX_COL_WIDTH, longest * _CHAR_PX + 28))
            # stretch=False: with many auto-sized columns, total width easily
            # exceeds the viewport - stretch=True would let ttk silently
            # compress every column back down toward minwidth to force a fit
            # (observed: every column pinned at 90px). Fixed widths + the
            # horizontal scrollbar is the correct combination here.
            self._tree.column(col, width=width, minwidth=_MIN_COL_WIDTH, anchor="w", stretch=False)

    def _render(self, rows: list[tuple]) -> None:
        self._tree.delete(*self._tree.get_children())
        for i, row in enumerate(rows):
            display_row = ["" if row[idx] is None else str(row[idx]) for idx in self._display_indices]
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(i), values=display_row, tags=(tag,))
        count = len(rows)
        self._count_label.configure(text=f"{count:,} record{'s' if count != 1 else ''}")

    def _apply_filter(self) -> None:
        self._render(self._current_visible_rows())

    def _handle_select(self, _event=None) -> None:
        if self._on_row_select is None:
            return
        selection = self._tree.selection()
        if not selection:
            return
        index = int(selection[0])
        visible_rows = self._current_visible_rows()
        if index < len(visible_rows):
            self._on_row_select(visible_rows[index])

    def _current_visible_rows(self) -> list[tuple]:
        """Rows matching the current search text (all fetched columns, not
        just the ones on screen, so a hidden id can still be searched)."""
        needle = self._search_var.get().strip().lower()
        if not needle:
            return self._all_rows
        return [
            row for row in self._all_rows
            if any(needle in str(v).lower() for v in row if v is not None)
        ]

    def clear_selection(self) -> None:
        self._tree.selection_remove(self._tree.selection())
