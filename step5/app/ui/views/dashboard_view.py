"""Dashboard / Home screen: system status and KPI tiles.

Navigation is exclusively via the left sidebar - this screen deliberately
has no nav buttons of its own.
"""
from __future__ import annotations

import customtkinter as ctk

from app.config import APP_NAME
from app.db.connection import Database
from app.services.dashboard_service import DashboardService
from app.ui.async_utils import run_in_background
from app.ui.dialogs import connection_error_message
from app.ui.theme import ACCENT, DANGER, SUCCESS, SURFACE, SURFACE_ALT, TEXT, TEXT_MUTED

_METRIC_ICONS = {
    "Schools": "\U0001F3EB",
    "Students": "\U0001F93D",
    "Teams": "\U0001F455",
    "Matches": "\U0001F3DF️",
    "Fantasy Users": "\U0001F464",
    "Active Rounds": "\U0001F501",
    "Squad Slots Filled": "\U0001F3AF",
    "Market Transactions": "\U0001F4B0",
}


class _KpiTile(ctk.CTkFrame):
    def __init__(self, master, title: str):
        super().__init__(master, corner_radius=14, fg_color=SURFACE)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=_METRIC_ICONS.get(title, "\U0001F4CC"),
                     font=ctk.CTkFont(size=20)).pack(padx=18, pady=(16, 0), anchor="w")
        self._value_label = ctk.CTkLabel(self, text="-", font=ctk.CTkFont(size=26, weight="bold"),
                                          text_color=TEXT)
        self._value_label.pack(padx=18, pady=(6, 0), anchor="w")
        ctk.CTkLabel(self, text=title, text_color=TEXT_MUTED, font=ctk.CTkFont(size=12)).pack(
            padx=18, pady=(0, 16), anchor="w"
        )

    def set_value(self, value) -> None:
        text = f"{value:,}" if isinstance(value, int) else str(value)
        self._value_label.configure(text=text)


class DashboardView(ctk.CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent", label_text="")
        self._metric_tiles: dict[str, _KpiTile] = {}

        self._build_header()
        self._build_status_card()
        self._build_kpi_grid()
        self.refresh()

    def _build_header(self) -> None:
        ctk.CTkLabel(self, text=f"Welcome back", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=TEXT).pack(anchor="w", pady=(4, 2))
        ctk.CTkLabel(
            self, text=f"{APP_NAME} - manage schools, teams, players and the fantasy league "
                       "from one place.",
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 20))

    def _build_status_card(self) -> None:
        card = ctk.CTkFrame(self, corner_radius=14, fg_color=SURFACE)
        card.pack(fill="x", pady=(0, 18))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=16)

        self._status_dot = ctk.CTkLabel(row, text="●", font=ctk.CTkFont(size=16),
                                         text_color=TEXT_MUTED, width=18)
        self._status_dot.pack(side="left")
        self._status_text = ctk.CTkLabel(row, text="Checking connection...", text_color=TEXT)
        self._status_text.pack(side="left", padx=(6, 12))
        ctk.CTkButton(row, text="Refresh", width=96, height=30, corner_radius=8,
                      fg_color=SURFACE_ALT, hover_color=ACCENT, text_color=TEXT,
                      command=self.refresh).pack(side="right")

    def _build_kpi_grid(self) -> None:
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 24))
        for col in range(4):
            grid.grid_columnconfigure(col, weight=1, uniform="metric")

        labels = ["Schools", "Students", "Teams", "Matches",
                  "Fantasy Users", "Active Rounds", "Squad Slots Filled", "Market Transactions"]
        for i, label in enumerate(labels):
            tile = _KpiTile(grid, label)
            tile.grid(row=i // 4, column=i % 4, sticky="ew", padx=6, pady=6)
            self._metric_tiles[label] = tile

    def refresh(self) -> None:
        self._status_text.configure(text="Checking connection...")
        self._status_dot.configure(text_color=TEXT_MUTED)

        def work():
            ok, info = Database.test_connection()
            metrics = DashboardService.metrics() if ok else {}
            return ok, info, metrics

        def on_done(result):
            ok, info, metrics = result
            if ok:
                self._status_dot.configure(text_color=SUCCESS)
                short_version = info.split(",")[0]
                self._status_text.configure(text=f"Connected - {short_version}")
                for label, tile in self._metric_tiles.items():
                    tile.set_value(metrics.get(label, "-"))
            else:
                self._status_dot.configure(text_color=DANGER)
                self._status_text.configure(text=f"Disconnected - {connection_error_message(Exception(info))}")

        def on_error(exc):
            self._status_dot.configure(text_color=DANGER)
            self._status_text.configure(text=f"Disconnected - {connection_error_message(exc)}")

        run_in_background(self, work, on_done, on_error)
