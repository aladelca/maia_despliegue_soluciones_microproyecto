"""Allow ``python -m online_shoppers`` to run the project CLI."""

from online_shoppers.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
