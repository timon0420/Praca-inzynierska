"""Lokalny punkt startowy backendowego serwisu analizy obrazu."""

import os

from backend.server import main


if __name__ == "__main__":
    os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "local-development-token")
    main()
