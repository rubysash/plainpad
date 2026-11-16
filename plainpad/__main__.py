"""Allow ``python -m plainpad`` to start the application."""

import sys

from plainpad.app import main

if __name__ == "__main__":
    sys.exit(main())
