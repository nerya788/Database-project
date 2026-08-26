"""Main application window: hierarchical sidebar navigation + view switching.

"Manage Data" is special: instead of a flat button like the other three
top-level items, it expands into a nested category -> table accordion
directly in the sidebar (see _build_manage_data_section). All Manage Data
navigation state (which category is expanded, which table is selected)
lives here; CrudView itself is a pure content pane with a public
`select_table(spec)` method and no navigation UI of its own.
"""
from __future__ import annotations

import customtkinter as ctk

from app.config import APP_MIN_SIZE, APP_NAME, DEFAULT_COLOR_THEME
from app.models.table_specs import TABLE_GROUPS, TableSpec
from app.ui.async_utils import start_dispatcher
from app.ui.theme import (
    ACCENT,
    BG,
    BORDER,
    SURFACE,
    SURFACE_ALT,
    TEXT,
    TEXT_MUTED,
    option_menu_style,
    style_treeview,
)
from app.ui.views.analytics_view import AnalyticsView
from app.ui.views.crud_view import CrudView
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.routines_view import RoutinesView

# This is a club-management client, not a study/demo tool - default to the
# polished dark theme (the user can still switch via the sidebar control).
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme(DEFAULT_COLOR_THEME)

# The 3 flat, single-click top-level items. "crud" ("Manage Data") is built
# separately by _build_manage_data_section since it expands into a nested
# accordion instead of being a single button.
FLAT_NAV_ITEMS = [
    ("dashboard", "Dashboard", "\U0001F3E0"),
    ("routines", "Actions", "⚡"),
    ("analytics", "Reports & Insights", "\U0001F4CA"),
]

_COLLAPSED_ARROW = "▸"  # ▸
_EXPANDED_ARROW = "▾"  # ▾


class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry(f"{APP_MIN_SIZE[0]}x{APP_MIN_SIZE[1]}")
        self.minsize(*APP_MIN_SIZE)
        self.configure(fg_color=BG)

        # Must start before any view is built: views may kick off background
        # work (e.g. DashboardView's connection check) from their own
        # constructor, and run_in_background() requires the dispatcher to
        # already be registered.
        start_dispatcher(self)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._views: dict[str, ctk.CTkBaseClass] = {}
        self._category_buttons: dict[str, ctk.CTkButton] = {}
        self._category_leaf_frames: dict[str, ctk.CTkFrame] = {}
        self._leaf_buttons: dict[str, ctk.CTkButton] = {}
        self._group_of_key: dict[str, str] = {
            spec.key: group for group, specs in TABLE_GROUPS for spec in specs
        }
        self._active_category: str | None = None
        self._active_leaf: str | None = None
        self._active_key: str | None = None

        self._build_sidebar()
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._build_views()
        self.show_view("dashboard")

        # Prime the Manage Data accordion (Core School Data expanded,
        # Schools selected and loading in the background) without actually
        # navigating there, so it's instantly ready the first time the user
        # clicks into Manage Data instead of starting from a blank state.
        self._expand_category(TABLE_GROUPS[0][0])
        self._activate_table(TABLE_GROUPS[0][1][0])

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=256, corner_radius=0, fg_color=SURFACE)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(26, 20))
        ctk.CTkLabel(brand, text="⚽", font=ctk.CTkFont(size=26)).pack(anchor="w")
        ctk.CTkLabel(
            brand, text="Football & Fantasy\nLeague Manager",
            font=ctk.CTkFont(size=15, weight="bold"), justify="left",
            text_color=TEXT,
        ).pack(anchor="w", pady=(6, 0))

        nav_scroll = ctk.CTkScrollableFrame(sidebar, fg_color="transparent", label_text="")
        nav_scroll.pack(fill="both", expand=True, padx=6)

        self._add_flat_nav_button(nav_scroll, *FLAT_NAV_ITEMS[0])
        self._build_manage_data_section(nav_scroll)
        for item in FLAT_NAV_ITEMS[1:]:
            self._add_flat_nav_button(nav_scroll, *item)

        ctk.CTkFrame(sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=20, pady=(10, 14))
        ctk.CTkLabel(sidebar, text="APPEARANCE", text_color=TEXT_MUTED,
                     font=ctk.CTkFont(size=10, weight="bold")).pack(padx=20, pady=(0, 6), anchor="w")
        ctk.CTkOptionMenu(
            sidebar, values=["Dark", "Light", "System"], command=self._change_appearance,
            width=196, height=32, corner_radius=8, fg_color=SURFACE_ALT,
            button_color=SURFACE_ALT, button_hover_color=BORDER,
            **option_menu_style(),
        ).pack(padx=14, pady=(0, 20))

    def _add_flat_nav_button(self, parent, key: str, label: str, icon: str) -> None:
        btn = ctk.CTkButton(
            parent, text=f"  {icon}   {label}", anchor="w", height=42,
            corner_radius=10, font=ctk.CTkFont(size=13),
            fg_color="transparent", text_color=TEXT_MUTED, hover_color=SURFACE_ALT,
            command=lambda k=key: self.show_view(k),
        )
        btn.pack(fill="x", pady=3)
        self._nav_buttons[key] = btn

    # -- "Manage Data": expandable category / table accordion -----------------
    def _build_manage_data_section(self, parent) -> None:
        header = ctk.CTkButton(
            parent, text="  \U0001F4C2   Manage Data", anchor="w", height=42,
            corner_radius=10, font=ctk.CTkFont(size=13),
            fg_color="transparent", text_color=TEXT_MUTED, hover_color=SURFACE_ALT,
            command=self._open_manage_data,
        )
        header.pack(fill="x", pady=3)
        self._nav_buttons["crud"] = header

        for group_name, specs in TABLE_GROUPS:
            cat_btn = ctk.CTkButton(
                parent, text=f"      {_COLLAPSED_ARROW}  {group_name}", anchor="w", height=34,
                corner_radius=8, font=ctk.CTkFont(size=12),
                fg_color="transparent", text_color=TEXT_MUTED, hover_color=SURFACE_ALT,
                command=lambda g=group_name: self._open_category(g),
            )
            cat_btn.pack(fill="x", pady=1)
            self._category_buttons[group_name] = cat_btn

            leaf_frame = ctk.CTkFrame(parent, fg_color="transparent")
            # Not packed yet - _expand_category() packs it (positioned via
            # after=cat_btn, so it always lands right below its own header
            # regardless of packing order elsewhere) only while it's the
            # single expanded category.
            self._category_leaf_frames[group_name] = leaf_frame

            for spec in specs:
                leaf_btn = ctk.CTkButton(
                    leaf_frame, text=spec.label, anchor="w", height=30,
                    corner_radius=8, font=ctk.CTkFont(size=12),
                    fg_color="transparent", text_color=TEXT_MUTED, hover_color=SURFACE_ALT,
                    command=lambda s=spec: self._open_table(s),
                )
                leaf_btn.pack(fill="x", padx=(28, 0), pady=1)
                self._leaf_buttons[spec.key] = leaf_btn

    def _open_manage_data(self) -> None:
        """Sidebar header click: navigate to Manage Data, defaulting to
        Core School Data / Schools only if nothing has been picked yet -
        revisiting keeps whatever the user last had open."""
        self.show_view("crud")
        if self._active_category is None:
            self._expand_category(TABLE_GROUPS[0][0])
        if self._active_leaf is None:
            self._activate_table(TABLE_GROUPS[0][1][0])

    def _open_category(self, group_name: str) -> None:
        """Category header click: navigate + expand, and default to that
        category's first table so the content pane never sits stale on a
        table from a different category."""
        self.show_view("crud")
        if self._active_category != group_name:
            self._expand_category(group_name)
            first_spec = next(specs for g, specs in TABLE_GROUPS if g == group_name)[0]
            self._activate_table(first_spec)

    def _expand_category(self, group_name: str) -> None:
        """Accordion behavior: at most one category's table list is shown
        at a time."""
        if self._active_category and self._active_category in self._category_leaf_frames:
            prev = self._active_category
            self._category_leaf_frames[prev].pack_forget()
            self._category_buttons[prev].configure(text=f"      {_COLLAPSED_ARROW}  {prev}")

        self._active_category = group_name
        self._category_leaf_frames[group_name].pack(
            fill="x", after=self._category_buttons[group_name]
        )
        self._category_buttons[group_name].configure(text=f"      {_EXPANDED_ARROW}  {group_name}")

    def _open_table(self, spec: TableSpec) -> None:
        """A specific table leaf was clicked: navigate + load it."""
        self.show_view("crud")
        self._activate_table(spec)

    def _activate_table(self, spec: TableSpec) -> None:
        """Load `spec` into the CRUD content pane and update sidebar
        highlighting - without itself changing which top-level view is on
        screen (used both by real clicks and by the startup priming call)."""
        group_name = self._group_of_key[spec.key]
        if self._active_category != group_name:
            self._expand_category(group_name)

        self._views["crud"].select_table(spec)

        self._active_leaf = spec.key
        for key, btn in self._leaf_buttons.items():
            active = key == spec.key
            btn.configure(
                fg_color=ACCENT if active else "transparent",
                text_color="#ffffff" if active else TEXT_MUTED,
            )

    def _build_views(self) -> None:
        self._views["dashboard"] = DashboardView(self._content)
        self._views["crud"] = CrudView(self._content)
        self._views["analytics"] = AnalyticsView(self._content)
        self._views["routines"] = RoutinesView(self._content)

    def show_view(self, key: str) -> None:
        if key == self._active_key:
            if key == "dashboard":
                self._views["dashboard"].refresh()
            return

        for k, btn in self._nav_buttons.items():
            active = k == key
            btn.configure(
                fg_color=ACCENT if active else "transparent",
                text_color="#ffffff" if active else TEXT_MUTED,
            )

        # Explicitly unmap every other view and map only the target one.
        # CTkScrollableFrame (Dashboard, Actions) does not reliably restack
        # via tkraise() alone when siblings include plain CTkFrames, so
        # grid()/grid_remove() is used instead of relying on z-order.
        for k, view in self._views.items():
            if k == key:
                view.grid(row=0, column=0, sticky="nsew")
            else:
                view.grid_remove()

        self._active_key = key
        if key == "dashboard":
            self._views["dashboard"].refresh()

    def _change_appearance(self, mode: str) -> None:
        ctk.set_appearance_mode(mode)
        self.after(50, self._restyle_after_theme_change)

    def _restyle_after_theme_change(self) -> None:
        style_treeview()
        for view in self._views.values():
            refresh = getattr(view, "refresh_theme", None)
            if callable(refresh):
                refresh()
