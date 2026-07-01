"""Verify the uvicorn import target 'app.main:app' loads and print its routes."""
from app.main import app


def main():
    print("app object:", type(app).__name__, "-", app.title)
    print("routes:")
    for r in app.routes:
        methods = getattr(r, "methods", None)
        path = getattr(r, "path", "")
        if not methods or path.startswith("/static"):
            continue
        print("  {:8} {}".format(",".join(sorted(methods)), path))


if __name__ == "__main__":
    main()
