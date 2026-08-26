"""Reports & Insights screen: analytical league reports, each with one
interactive filter, run in the background with a visible loading state.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from typing import Optional

import customtkinter as ctk

from app.services.analytics_service import REPORTS, AnalyticsService, ReportSpec
from app.ui.async_utils import run_in_background
from app.ui.dialogs import show_db_error, show_error
from app.ui.theme import (
    ACCENT,
    ACCENT_HOVER,
    BORDER,
    SURFACE,
    SURFACE_ALT,
    TEXT,
    TEXT_MUTED,
    option_menu_style,
)
from app.ui.widgets.data_table import DataTable


class AnalyticsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._report: Optional[ReportSpec] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._table = DataTable(self)
        self._table.grid(row=1, column=0, sticky="nsew")

        self._select_report(REPORTS[0])

    def refresh_theme(self) -> None:
        self._table.refresh_theme()

    def _build_header(self) -> None:
        card = ctk.CTkFrame(self, corner_radius=14, fg_color=SURFACE)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text="Report", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w", padx=(20, 10), pady=(18, 4))
        self._report_menu = ctk.CTkOptionMenu(
            card, values=[r.label for r in REPORTS], command=self._on_report_chosen, width=440,
            height=34, corner_radius=8, fg_color=SURFACE_ALT,
            button_color=SURFACE_ALT, button_hover_color=BORDER,
            **option_menu_style(),
        )
        self._report_menu.grid(row=0, column=1, sticky="w", pady=(18, 4))

        self._description = ctk.CTkLabel(card, text="", text_color=TEXT_MUTED, anchor="w",
                                          wraplength=760, justify="left")
        self._description.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))

        filter_row = ctk.CTkFrame(card, fg_color="transparent")
        filter_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 18))

        self._filter_label = ctk.CTkLabel(filter_row, text="", text_color=TEXT)
        self._filter_label.pack(side="left", padx=(0, 8))
        self._filter_var = tk.StringVar()
        self._filter_entry = ctk.CTkEntry(filter_row, textvariable=self._filter_var, width=120,
                                           height=34, corner_radius=8)
        self._filter_entry.pack(side="left", padx=(0, 14))

        self._run_btn = ctk.CTkButton(filter_row, text="Run Report", width=130, height=34,
                                       corner_radius=8, fg_color=ACCENT,
                                       hover_color=ACCENT_HOVER, command=self._run)
        self._run_btn.pack(side="left")

        self._progress = ttk.Progressbar(filter_row, mode="indeterminate", length=160)
        self._status_label = ctk.CTkLabel(filter_row, text="", text_color=TEXT_MUTED)
        self._status_label.pack(side="left", padx=(12, 0))

    def _on_report_chosen(self, label: str) -> None:
        report = next(r for r in REPORTS if r.label == label)
        self._select_report(report)

    def _select_report(self, report: ReportSpec) -> None:
        self._report = report
        self._report_menu.set(report.label)
        self._description.configure(text=report.description)
        self._filter_label.configure(text=report.filter_label + ":")
        self._filter_var.set(str(report.filter_default))
        self._table.set_data([], [])

        def compute_default():
            return AnalyticsService.suggest_default(report)

        def on_done(value):
            if report is self._report:
                formatted = f"{float(value):.2f}" if report.filter_kind == "decimal" else str(int(value))
                self._filter_var.set(formatted)

        run_in_background(self, compute_default, on_done, lambda exc: None)

    def _set_loading(self, loading: bool) -> None:
        if loading:
            self._run_btn.configure(state="disabled")
            self._progress.pack(side="left", padx=(12, 8))
            self._progress.start(12)
            self._status_label.configure(text="Running...")
        else:
            self._progress.stop()
            self._progress.pack_forget()
            self._run_btn.configure(state="normal")

    def _run(self) -> None:
        report = self._report
        raw = self._filter_var.get().strip()
        try:
            filter_value = int(raw) if report.filter_kind == "int" else float(raw)
        except ValueError:
            show_error("Invalid Filter", f'"{report.filter_label}" must be a number.')
            return

        self._set_loading(True)

        def work():
            return AnalyticsService.run(report, filter_value)

        def on_done(result):
            self._set_loading(False)
            self._status_label.configure(text="")
            columns, rows = result
            self._table.set_data(columns, rows)

        def on_error(exc):
            self._set_loading(False)
            self._status_label.configure(text="")
            show_db_error(exc)

        run_in_background(self, work, on_done, on_error)
