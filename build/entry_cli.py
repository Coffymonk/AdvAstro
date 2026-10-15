"""Entry point for the bundled command-line executable."""

import multiprocessing

from advastro.cli import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
