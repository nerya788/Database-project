"""Shared visual language for the app: a premium, dark-navy sports-dashboard
palette, spacing/radius constants, and a ttk.Treeview styler.

CustomTkinter widgets auto-restyle on appearance-mode toggle when given a
`(light_value, dark_value)` tuple - so every color below is exposed as a
tuple for direct use in `fg_color=`/`text_color=` etc, and CTk repaints them
automatically with no manual refresh code needed. Only the ttk.Treeview (used
for the data grid) is NOT theme-aware on its own; `style_treeview()` /
`row_stripe_colors()` resolve the *current* mode's colors and must be
re-applied explicitly after a theme switch (app_window.py does this).
"""
from __future__ import annotations

import tkinter.ttk as ttk

import customtkinter as ctk

# -- Status colors (same in both modes) ---------------------------------------
SUCCESS = "#2fa572"
DANGER = "#e5484d"
WARNING = "#e5a010"
MUTED = "#8a8a8a"

# -- Layout constants ----------------------------------------------------------
PAD = 16
CARD_CORNER = 14
FIELD_CORNER = 8

# -- (light, dark) palette tuples - pass directly as CTk color options -------
BG = ("#f2f4f7", "#1a1d24")
SURFACE = ("#ffffff", "#242832")
SURFACE_ALT = ("#eef1f6", "#2b303c")
BORDER = ("#dde2ea", "#343a46")
TEXT = ("#1a1d24", "#eef1f6")
TEXT_MUTED = ("#6b7280", "#9aa3b2")
ACCENT = ("#2563eb", "#3d8bfd")
ACCENT_HOVER = ("#3b76f0", "#5b9dff")
ACCENT_TEXT = ("#ffffff", "#ffffff")

_DARK_RESOLVED = {
    "bg": BG[1], "surface": SURFACE[1], "surface_alt": SURFACE_ALT[1], "border": BORDER[1],
    "text": TEXT[1], "text_muted": TEXT_MUTED[1], "accent": ACCENT[1], "accent_hover": ACCENT_HOVER[1],
}
_LIGHT_RESOLVED = {
    "bg": BG[0], "surface": SURFACE[0], "surface_alt": SURFACE_ALT[0], "border": BORDER[0],
    "text": TEXT[0], "text_muted": TEXT_MUTED[0], "accent": ACCENT[0], "accent_hover": ACCENT_HOVER[0],
}


def option_menu_style() -> dict:
    """Standard color kwargs for every CTkOptionMenu in the app.

    CTkOptionMenu does not inherit readable text/dropdown colors just from
    fg_color - left at its CTk theme defaults, its text and its popup list
    can end up low-contrast (washed out) against our custom navy/slate
    palette in one or both appearance modes. Every CTkOptionMenu should
    spread this dict in, e.g. `ctk.CTkOptionMenu(master, values=[...],
    **option_menu_style())`, then still set its own fg_color/button_color.
    """
    return {
        "text_color": TEXT,
        "dropdown_fg_color": SURFACE_ALT,
        "dropdown_text_color": TEXT,
        "dropdown_hover_color": ACCENT,
    }


def palette() -> dict:
    """The *resolved* palette for the current appearance mode - only needed
    for non-CTk widgets (ttk.Treeview). CTk widgets should use the tuple
    constants above instead, so they auto-restyle on theme toggle."""
    return _DARK_RESOLVED if ctk.get_appearance_mode() == "Dark" else _LIGHT_RESOLVED


def row_stripe_colors() -> tuple[str, str]:
    """(even_row_bg, odd_row_bg) for the current appearance mode."""
    p = palette()
    return p["surface"], p["surface_alt"]


def style_treeview(style: "ttk.Style | None" = None) -> ttk.Style:
    style = style or ttk.Style()
    p = palette()

    style.theme_use("clam")
    style.configure(
        "App.Treeview",
        background=p["surface"],
        fieldbackground=p["surface"],
        foreground=p["text"],
        rowheight=30,
        borderwidth=0,
        font=("Segoe UI", 11),
    )
    style.map(
        "App.Treeview",
        background=[("selected", p["accent"])],
        foreground=[("selected", "#ffffff")],
    )
    style.configure(
        "App.Treeview.Heading",
        background=p["surface_alt"],
        foreground=p["text_muted"],
        borderwidth=0,
        font=("Segoe UI Semibold", 10),
        relief="flat",
    )
    style.map("App.Treeview.Heading", background=[("active", p["surface_alt"])])
    return style
