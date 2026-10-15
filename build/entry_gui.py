"""Entry point for the bundled desktop app."""

import multiprocessing

from advastro.gui.app import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
