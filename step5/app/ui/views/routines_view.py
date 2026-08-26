"""Actions screen: the day-to-day club operations - valuing a player,
checking a squad against roster rules, running a transfer, and settling a
league round. Each is a compact action card with plain-language copy; the
outcome is shown as a colored result banner, not a raw log dump.
"""
from __future__ import annotations

import logging
import re
import tkinter as tk

import customtkinter as ctk

from app.models.table_specs import FK_ROUNDS, FK_SCHOOLS, FK_USERS, fk_students_by_school
from app.services.routines_service import RoutinesService
from app.ui.async_utils import run_in_background
from app.ui.dialogs import confirm, show_db_error, show_error
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
from app.ui.widgets.fk_picker import FkPicker

_BANNER_STYLES = {
    "success": (SUCCESS, "✅"),
    "warning": (WARNING, "⚠️"),
    "error": (DANGER, "❌"),
    "info": (ACCENT, "ℹ️"),
}

# sp_process_player_transfer's own message always embeds the raw price as
# "... for <number>" (see step4/procedure1.sql) - used to recover it for the
# banner without ever showing the raw user_id/player_id the procedure also
# embeds in that string. NUMERIC(10,2) is always formatted with exactly 2
# decimal digits, so \d+\.\d{2} (not a greedy [\d.]+) is required - the
# looser class also swallowed the sentence's own trailing "." (e.g. "for
# 72.10." -> "72.10." -> float() ValueError).
_TRANSFER_PRICE_RE = re.compile(r"for\s+\$?(\d+\.\d{2})")


def _humanize_transfer_outcome(
    data: dict, user_id, player_id, user_label: str, player_label: str, action: str
) -> tuple[str, str]:
    """(banner_kind, message) for a completed transfer - built from the
    already-resolved picker labels, never the raw ids the database
    procedure's own message is written in terms of."""
    if data["success"]:
        verb = "bought" if action == "BUY" else "sold"
        match = _TRANSFER_PRICE_RE.search(data["message"] or "")
        price_text = f" for ${float(match.group(1)):,.2f}" if match else ""
        return "success", f'Manager "{user_label}" successfully {verb} player "{player_label}"{price_text}.'

    # Rejection reasons vary (insufficient budget, already owned, squad
    # full, ...) - rather than re-deriving each one, swap the raw ids the
    # procedure's message was built from for the names already on screen.
    friendly = data["message"] or "The transfer could not be completed."
    friendly = friendly.replace(str(player_id), f'"{player_label}"')
    friendly = friendly.replace(str(user_id), f'"{user_label}"')
    return "error", friendly


class _ResultBanner(ctk.CTkFrame):
    """A colored callout that appears only once an action has produced a
    result - never an empty box sitting on the screen by default."""

    def __init__(self, master):
        super().__init__(master, corner_radius=10, fg_color=SURFACE_ALT, height=0)
        self._icon = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=16))
        self._icon.pack(side="left", padx=(14, 8), pady=12)
        self._text = ctk.CTkLabel(self, text="", anchor="w", justify="left",
                                   font=ctk.CTkFont(size=13), wraplength=640)
        self._text.pack(side="left", fill="x", expand=True, padx=(0, 14), pady=12)

    def show(self, kind: str, message: str) -> None:
        color, icon = _BANNER_STYLES.get(kind, _BANNER_STYLES["info"])
        self.configure(fg_color=color)
        self._icon.configure(text=icon)
        self._text.configure(text=message, text_color="#ffffff")
        self.pack(fill="x", pady=(14, 0))

    def hide(self) -> None:
        self.pack_forget()


class _ActionCard(ctk.CTkFrame):
    """A single, focused workspace for one action - full width, with the
    actual form controls centered in the available space rather than
    pinned to the left edge, since a tab now shows exactly one of these at
    a time instead of four packed into a 2x2 grid."""

    def __init__(self, master, icon: str, title: str, description: str):
        super().__init__(master, corner_radius=18, fg_color=SURFACE)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))
        ctk.CTkLabel(header, text=icon, font=ctk.CTkFont(size=30)).pack(side="left", padx=(0, 14))
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=21, weight="bold"),
                     text_color=TEXT).pack(side="left")

        ctk.CTkLabel(self, text=description, text_color=TEXT_MUTED, anchor="w",
                     justify="left", wraplength=760, font=ctk.CTkFont(size=13)).grid(
            row=1, column=0, sticky="ew", padx=32, pady=(8, 26)
        )

        # No sticky="ew": the body's cell spans the full card width, but the
        # body itself only takes its natural (form) width - tkinter grid
        # centers a widget that doesn't stick to a side, which is exactly
        # the "centered form inputs" look this screen wants.
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, padx=32)

        self.banner_slot = ctk.CTkFrame(self, fg_color="transparent")
        self.banner_slot.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 0))
        self.banner = _ResultBanner(self.banner_slot)

        ctk.CTkFrame(self, fg_color="transparent", height=32).grid(row=4, column=0)

    def set_busy(self, busy: bool, button: ctk.CTkButton, busy_text: str, idle_text: str) -> None:
        button.configure(state="disabled" if busy else "normal", text=busy_text if busy else idle_text)


_TABS = [
    ("market_value", "\U0001F4B0", "Market Value Calculator"),
    ("compliance", "\U0001F4CB", "Squad Rule Evaluation"),
    ("transfer", "\U0001F504", "Transfer Market"),
    ("settle", "\U0001F3C6", "Settle League Round"),
]


class RoutinesView(ctk.CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent", label_text="")

        ctk.CTkLabel(self, text="Actions", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=TEXT).pack(anchor="w", pady=(4, 2))
        ctk.CTkLabel(self, text="Run the day-to-day club and league operations.",
                     text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 20))

        self._build_tab_bar()

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=1)

        self._cards: dict[str, _ActionCard] = {
            "market_value": self._build_market_value_card(content),
            "compliance": self._build_compliance_card(content),
            "transfer": self._build_transfer_card(content),
            "settle": self._build_settle_card(content),
        }
        for card in self._cards.values():
            card.grid(row=0, column=0, sticky="new")

        self._select_tab(_TABS[0][0])

    def _build_tab_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=14)
        bar.pack(fill="x", pady=(0, 20))
        row = ctk.CTkFrame(bar, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=14)

        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        for key, icon, label in _TABS:
            btn = ctk.CTkButton(
                row, text=f"{icon}  {label}", height=40, corner_radius=10,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="transparent", text_color=TEXT_MUTED, hover_color=SURFACE_ALT,
                command=lambda k=key: self._select_tab(k),
            )
            btn.pack(side="left", padx=(0, 8))
            self._tab_buttons[key] = btn

    def _select_tab(self, key: str) -> None:
        for k, btn in self._tab_buttons.items():
            active = k == key
            btn.configure(
                fg_color=ACCENT if active else "transparent",
                text_color="#ffffff" if active else TEXT_MUTED,
            )
        # grid()/grid_remove() rather than tkraise(): stacking multiple
        # frames and relying on raise order to hide the rest has proven
        # unreliable in this app (see the Dashboard-nav fix a few turns
        # back) - only ever mapping the active card sidesteps that outright.
        for k, card in self._cards.items():
            if k == key:
                card.grid()
            else:
                card.grid_remove()

    # -- Calculate Market Value -----------------------------------------------
    def _build_market_value_card(self, master) -> _ActionCard:
        card = _ActionCard(
            master, "\U0001F4B0", "Market Value Calculator",
            "Recalculate a player's current value based on their recent match performance.",
        )

        school_row = ctk.CTkFrame(card.body, fg_color="transparent")
        school_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(school_row, text="School", text_color=TEXT_MUTED,
                     font=ctk.CTkFont(size=11)).pack(anchor="w")

        player_row = ctk.CTkFrame(card.body, fg_color="transparent")
        player_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(player_row, text="Player", text_color=TEXT_MUTED,
                     font=ctk.CTkFont(size=11)).pack(anchor="w")

        # Built before the School picker so its on_change callback (below)
        # can already refer to it. Starts disabled/empty - with 25,000
        # students, showing "everyone" by default just clumps the capped
        # dropdown on whichever surname happens to sort first; scoping to
        # one school (~50 students) keeps it small and lets a school-first
        # choice reach any player, not just the alphabetically-first ones.
        picker = FkPicker(player_row, width=260, height=34)
        picker.set_placeholder("Select a school first")
        picker.set_enabled(False)
        picker.pack(anchor="w", pady=(2, 0))

        def on_school_change(school_id):
            if school_id is None:
                picker.set_placeholder("Select a school first")
                picker.set_enabled(False)
                return
            picker.set_enabled(True)
            picker.load_async(fk_students_by_school(school_id))

        school_picker = FkPicker(school_row, FK_SCHOOLS, width=260, height=34, on_change=on_school_change)
        school_picker.pack(anchor="w", pady=(2, 0))

        button_row = ctk.CTkFrame(card.body, fg_color="transparent")
        button_row.pack(fill="x")
        run_btn = ctk.CTkButton(button_row, text="Calculate", width=120, height=34, corner_radius=8,
                                 fg_color=ACCENT, hover_color=ACCENT_HOVER)
        run_btn.pack(side="left")

        def run():
            student_id = picker.get_id()
            if student_id is None:
                show_error("No Selection", "Choose a school, then a player.")
                return
            card.set_busy(True, run_btn, "Calculating...", "Calculate")
            card.banner.hide()

            def work():
                return RoutinesService.calculate_player_market_value(student_id)

            def on_done(result):
                card.set_busy(False, run_btn, "Calculating...", "Calculate")
                if result.value is None:
                    card.banner.show("error", "Could not calculate a value for this player.")
                else:
                    card.banner.show(
                        "info", f"Updated market value: ${result.value:,.2f}"
                    )

            def on_error(exc):
                card.set_busy(False, run_btn, "Calculating...", "Calculate")
                show_db_error(exc)

            run_in_background(self, work, on_done, on_error)

        run_btn.configure(command=run)
        return card

    # -- Evaluate Squad Rules ---------------------------------------------------
    def _build_compliance_card(self, master) -> _ActionCard:
        card = _ActionCard(
            master, "\U0001F4CB", "Squad Rule Evaluation",
            "Check whether a manager's squad meets the league's roster requirements.",
        )
        picker = FkPicker(card.body, FK_USERS, width=260, height=34)
        picker.pack(side="left", padx=(0, 10))
        run_btn = ctk.CTkButton(card.body, text="Check Squad", width=120, height=34, corner_radius=8,
                                 fg_color=ACCENT, hover_color=ACCENT_HOVER)
        run_btn.pack(side="left")

        def run():
            user_id = picker.get_id()
            if user_id is None:
                show_error("No Selection", "Choose a manager first.")
                return
            card.set_busy(True, run_btn, "Checking...", "Check Squad")
            card.banner.hide()

            def work():
                return RoutinesService.evaluate_squad_compliance(user_id)

            def on_done(result):
                card.set_busy(False, run_btn, "Checking...", "Check Squad")
                data = result.value
                if data is None:
                    card.banner.show("error", "Could not evaluate this squad.")
                    return
                kind = "success" if data["is_compliant"] else "warning"
                summary = (
                    f"{data['status_message']}  ({data['total_players']} players, "
                    f"{data['starting_count']} starting, squad value "
                    f"${data['squad_value']:,.2f})"
                )
                card.banner.show(kind, summary)

            def on_error(exc):
                card.set_busy(False, run_btn, "Checking...", "Check Squad")
                show_db_error(exc)

            run_in_background(self, work, on_done, on_error)

        run_btn.configure(command=run)
        return card

    # -- Transfer Market ----------------------------------------------------------
    def _build_transfer_card(self, master) -> _ActionCard:
        card = _ActionCard(
            master, "\U0001F504", "Transfer Market",
            "Buy or sell a player on behalf of a fantasy manager.",
        )

        manager_row = ctk.CTkFrame(card.body, fg_color="transparent")
        manager_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(manager_row, text="Manager", text_color=TEXT_MUTED,
                     font=ctk.CTkFont(size=11)).pack(anchor="w")
        user_picker = FkPicker(manager_row, FK_USERS, width=260, height=34)
        user_picker.pack(anchor="w", pady=(2, 0))

        school_row = ctk.CTkFrame(card.body, fg_color="transparent")
        school_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(school_row, text="School", text_color=TEXT_MUTED,
                     font=ctk.CTkFont(size=11)).pack(anchor="w")

        player_row = ctk.CTkFrame(card.body, fg_color="transparent")
        player_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(player_row, text="Player", text_color=TEXT_MUTED,
                     font=ctk.CTkFont(size=11)).pack(anchor="w")

        # Same school-first cascade as Calculate Market Value, and for the
        # same reason: capping the dropdown at 80 entries out of 25,000
        # otherwise strands the list on whichever surname sorts first.
        player_picker = FkPicker(player_row, width=260, height=34)
        player_picker.set_placeholder("Select a school first")
        player_picker.set_enabled(False)
        player_picker.pack(anchor="w", pady=(2, 0))

        def on_school_change(school_id):
            if school_id is None:
                player_picker.set_placeholder("Select a school first")
                player_picker.set_enabled(False)
                return
            player_picker.set_enabled(True)
            player_picker.load_async(fk_students_by_school(school_id))

        school_picker = FkPicker(school_row, FK_SCHOOLS, width=260, height=34, on_change=on_school_change)
        school_picker.pack(anchor="w", pady=(2, 0))

        row3 = ctk.CTkFrame(card.body, fg_color="transparent")
        row3.pack(fill="x")
        action_var = tk.StringVar(value="BUY")
        action_menu = ctk.CTkOptionMenu(row3, values=["BUY", "SELL"], variable=action_var, width=90,
                                         height=34, fg_color=SURFACE_ALT, button_color=SURFACE_ALT,
                                         button_hover_color=ACCENT, **option_menu_style())
        action_menu.pack(side="left", padx=(0, 10))
        run_btn = ctk.CTkButton(row3, text="Execute Transfer", width=150, height=34, corner_radius=8,
                                 fg_color=ACCENT, hover_color=ACCENT_HOVER)
        run_btn.pack(side="left")

        def run():
            user_id = user_picker.get_id()
            player_id = player_picker.get_id()
            if user_id is None or player_id is None:
                show_error("No Selection", "Choose a manager, a school, and a player.")
                return
            user_label = user_picker.get_label()
            player_label = player_picker.get_label()
            action = action_var.get()
            card.set_busy(True, run_btn, "Processing...", "Execute Transfer")
            card.banner.hide()

            def work():
                return RoutinesService.process_player_transfer(user_id, player_id, action)

            def on_done(result):
                card.set_busy(False, run_btn, "Processing...", "Execute Transfer")
                try:
                    kind, message = _humanize_transfer_outcome(
                        result.value, user_id, player_id, user_label, player_label, action
                    )
                except Exception:  # noqa: BLE001 - never fail silently with no user feedback
                    logging.getLogger(__name__).exception("Failed to format transfer outcome")
                    kind, message = ("success" if result.value.get("success") else "error",
                                      "The transfer completed, but its result could not be displayed.")
                card.banner.show(kind, message)

            def on_error(exc):
                card.set_busy(False, run_btn, "Processing...", "Execute Transfer")
                show_db_error(exc)

            run_in_background(self, work, on_done, on_error)

        run_btn.configure(command=run)
        return card

    # -- Settle League Round ---------------------------------------------------
    def _build_settle_card(self, master) -> _ActionCard:
        card = _ActionCard(
            master, "\U0001F3C6", "Settle League Round",
            "Revalue every squad player, archive prices, and advance the league to the next round.",
        )
        picker = FkPicker(card.body, FK_ROUNDS, width=260, height=34)
        picker.pack(side="left", padx=(0, 10))
        run_btn = ctk.CTkButton(card.body, text="Settle Round", width=140, height=34, corner_radius=8,
                                 fg_color=WARNING, hover_color="#c98c0b")
        run_btn.pack(side="left")

        def run():
            round_id = picker.get_id()
            if round_id is None:
                show_error("No Selection", "Choose a round first.")
                return
            if not confirm("Confirm Settlement",
                            "Settling a round revalues players and advances the league. Continue?"):
                return
            card.set_busy(True, run_btn, "Settling...", "Settle Round")
            card.banner.hide()

            def work():
                return RoutinesService.settle_round(round_id)

            def on_done(result):
                card.set_busy(False, run_btn, "Settling...", "Settle Round")
                data = result.value
                kind = "success" if data["errors_encountered"] == 0 else "warning"
                message = f"{data['players_processed']} players revalued"
                if data["errors_encountered"]:
                    message += f", {data['errors_encountered']} could not be processed"
                message += ". The round is now complete."
                card.banner.show(kind, message)

            def on_error(exc):
                card.set_busy(False, run_btn, "Settling...", "Settle Round")
                show_db_error(exc)

            run_in_background(self, work, on_done, on_error)

        run_btn.configure(command=run)
        return card
