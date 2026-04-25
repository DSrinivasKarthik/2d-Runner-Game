"""Legacy entry point.

The project is scene-based now. This module intentionally stays as a thin
compatibility wrapper so old commands like `python runnergame.py` still work.
"""

from main import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()
