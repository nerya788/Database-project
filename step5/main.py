"""Entry point for the School Football & Fantasy League Manager desktop app.

Run with:  python main.py   (from inside step5/, with the venv active)
"""
import logging

from app.ui.app_window import AppWindow


def main() -> None:
    # Every DB error dialog logs the full technical exception here rather
    # than showing it to the user - basicConfig() ensures that actually
    # reaches the console instead of being silently dropped.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = AppWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
