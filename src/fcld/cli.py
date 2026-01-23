"""CLI entrypoint for FCLD."""

from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fcld",
        description="FCLD - FleetCommand Lighting Designer",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    demo_parser = subparsers.add_parser("demo-basic", help="Run the basic demo show")
    demo_parser.add_argument(
        "--start-at",
        type=float,
        default=0.0,
        help="Start time in seconds (default: 0.0)",
    )
    demo_parser.add_argument(
        "--fps",
        type=float,
        default=40.0,
        help="Frames per second (default: 40)",
    )

    args = parser.parse_args()

    if args.command == "demo-basic":
        run_demo_basic(args.start_at, args.fps)
    else:
        parser.print_help()
        sys.exit(1)


def run_demo_basic(start_at: float, fps: float) -> None:
    """Run the basic demo show."""
    try:
        from shows.basic_show import run
    except ImportError:
        sys.path.insert(0, ".")
        try:
            from shows.basic_show import run
        except ImportError:
            print("ERROR: Could not import basic_show.")
            print("Make sure you're running from the project root directory.")
            sys.exit(1)

    ola_host = os.environ.get("OLA_HOST", "localhost")
    ola_port = os.environ.get("OLA_PORT", "9010")

    print("FCLD - Basic Demo")
    print(f"  FPS: {fps}")
    print(f"  Start at: {start_at}s")
    print(f"  Universe: 1")
    print(f"  OLA: {ola_host}:{ola_port}")
    print()
    print("Press Ctrl+C to stop.")
    print()

    run(start_at=start_at, fps=fps)


if __name__ == "__main__":
    main()
