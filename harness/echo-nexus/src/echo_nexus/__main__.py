"""Public CLI; headless capture uses the same TUI widgets as interactive use."""
import argparse
import asyncio
import json
from pathlib import Path

from . import __version__
from .config import detect


def main():
    p = argparse.ArgumentParser(description="echo-nexus · developer: rxlabs · open terminal harness")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--doctor", action="store_true", help="Detect local tools without starting them")
    p.add_argument("--connect", help="Connect a saved profile on startup")
    p.add_argument("--no-connect", action="store_true", help="Skip automatic saved connection")
    p.add_argument("--backend", help="Operator-provided echo-nexus-backend-v1 manifest")
    p.add_argument("--no-stars", action="store_true", help="Disable decorative animation")
    p.add_argument("--capture", metavar="PATH.svg", help="Capture the real TUI as SVG, headlessly")
    p.add_argument("--command", default="/help", help="Command to use during capture")
    p.add_argument("--size", default="132x46", help="Capture columns x rows")
    args = p.parse_args()
    if args.doctor:
        print(json.dumps({"harness": __version__, "developer": "rxlabs", "tools": detect()}, indent=2))
        return
    from .app import Nexus
    app = Nexus(backend=args.backend, stars=not args.no_stars, connect=args.connect,
                autoconnect=not (args.no_connect or args.capture))
    if args.capture:
        width, height = map(int, args.size.split("x"))
        async def capture():
            async with app.run_test(size=(width, height)) as pilot:
                await app.execute(args.command)
                await pilot.pause(0.2)
                target = Path(args.capture)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(app.export_screenshot(title="echo-nexus · developer: rxlabs"))
        asyncio.run(capture())
    else:
        app.run()


if __name__ == "__main__":
    main()
