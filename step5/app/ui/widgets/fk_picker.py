"""A foreign-key selector that is safe for very large reference tables.

Root cause of a real, reproduced crash: `Teams.captain_student_id` (and
several other columns) reference `Students` / `Global_Equipment`, each
~25,000 rows. Handing that many entries to a native CTkOptionMenu (backed
by a Tk `Menu` widget, one native menu item per entry) segfaults the
Tcl/Tk runtime outright - it is not a Python exception and cannot be
caught with try/except.

FkPicker avoids this unconditionally: the full (id, label) option list is
kept in a plain Python dict (cheap - tens of thousands of tuples is
nothing), but the on-screen CTkOptionMenu is only ever fed a small,
search-filtered slice (`_MAX_VISIBLE_OPTIONS`). A search box lets the user
find any entry by typing.

The currently-selected value is derived by reading whatever label the
CTkOptionMenu is currently displaying (`self._menu.get()`) rather than
cached in separate state - so the displayed label and the value returned
by `get_id()` can never desync, even while the visible list is capped.
"""
from __future__ import annotations

import tkinter as tk
from typing import Optional

import customtkinter as ctk

from app.services.crud_service import CrudService
from app.ui.async_utils import run_in_background
from app.ui.dialogs import show_db_error
from app.ui.theme import ACCENT, SURFACE_ALT, option_menu_style

_MAX_VISIBLE_OPTIONS = 80
_PLACEHOLDER = "-- Select --"
_NONE_LABEL = "(none)"


class FkPicker(ctk.CTkFrame):
    def __init__(self, master, fk_ref=None, nullable: bool = False,
                 width: int = 260, height: int = 34, on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._nullable = nullable
        self._by_label: dict[str, object] = {}
        self._by_id: dict[object, str] = {}
        self._pinned_label: Optional[str] = None  # force-included even if filtered out
        # Fires with the newly-picked id whenever the user (not code) changes
        # the selection - e.g. so a School picker can cascade into a Player
        # picker. CTkOptionMenu.set() (used for all programmatic changes in
        # this class) does NOT invoke `command`, so this never fires from
        # our own refreshes - only real clicks.
        self._on_change = on_change

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_menu())
        self._search = ctk.CTkEntry(self, textvariable=self._search_var, width=width, height=height,
                                     corner_radius=8, placeholder_text="Type to search...")
        self._search.pack(fill="x")

        self._menu = ctk.CTkOptionMenu(
            self, values=["Loading..."], width=width, height=height, corner_radius=8,
            fg_color=SURFACE_ALT, button_color=SURFACE_ALT, button_hover_color=ACCENT,
            command=self._handle_user_pick, **option_menu_style(),
        )
        self._menu.pack(fill="x", pady=(6, 0))

        if fk_ref is not None:
            self.load_async(fk_ref)

    def _handle_user_pick(self, _label: str) -> None:
        if self._on_change is not None:
            self._on_change(self.get_id())

    def load_async(self, fk_ref) -> None:
        def work():
            return CrudService.fk_options(fk_ref)

        def on_done(options):
            self.set_options(options)

        def on_error(exc):
            self._menu.configure(values=["Unable to load"])
            self._menu.set("Unable to load")
            show_db_error(exc)

        run_in_background(self, work, on_done, on_error)

    def set_options(self, options: list[tuple]) -> None:
        self._by_label = {}
        self._by_id = {}
        for opt_id, opt_label in options:
            text = str(opt_label)
            self._by_label[text] = opt_id
            self._by_id[opt_id] = text
        self._pinned_label = None
        self._search_var.set("")  # triggers _refresh_menu with a clean slate

    def _refresh_menu(self) -> None:
        needle = self._search_var.get().strip().lower()
        if needle:
            matches = [lbl for lbl in self._by_label if needle in lbl.lower()][:_MAX_VISIBLE_OPTIONS]
        else:
            matches = list(self._by_label.keys())[:_MAX_VISIBLE_OPTIONS]
            if self._pinned_label and self._pinned_label not in matches:
                matches = [self._pinned_label] + matches

        leading = [_NONE_LABEL] if self._nullable else [_PLACEHOLDER]
        values = leading + matches
        if not matches and not self._by_label:
            values = ["Loading..."]

        self._menu.configure(values=values)
        if self._pinned_label and self._pinned_label in values:
            self._menu.set(self._pinned_label)
        else:
            self._menu.set(values[0])

    def get_id(self):
        return self._by_label.get(self._menu.get())

    def get_label(self) -> str:
        """The currently displayed text - already the resolved, human-
        readable name (or a placeholder if nothing valid is selected)."""
        return self._menu.get()

    def set_selected(self, id_value) -> None:
        self._pinned_label = self._by_id.get(id_value)
        self._search_var.set("")  # triggers _refresh_menu, which pins + selects it

    def clear(self) -> None:
        self._pinned_label = None
        self._search_var.set("")

    def set_placeholder(self, text: str) -> None:
        """Show a static placeholder (e.g. "Select a school first") with no
        options loaded - distinct from the transient "Loading..." state a
        real fetch shows, so an intentionally-empty cascade step doesn't
        look like it's stuck loading."""
        self._by_label = {}
        self._by_id = {}
        self._pinned_label = None
        self._search_var.set("")
        self._menu.configure(values=[text])
        self._menu.set(text)

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        try:
            self._search.configure(state=state)
            self._menu.configure(state=state)
        except Exception:
            pass
