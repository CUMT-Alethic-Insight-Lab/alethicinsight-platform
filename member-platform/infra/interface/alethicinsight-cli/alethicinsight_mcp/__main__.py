import argparse
import math

from .server import CliRunner, serve


def main():
    parser = argparse.ArgumentParser(description="Alethic local stdio MCP adapter")
    parser.add_argument("--cli", help="Explicit trusted local CLI executable path (default: current Python module)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per CLI invocation timeout, 0.05–120 seconds")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or not 0.05 <= args.timeout <= 120:
        parser.error("--timeout must be between 0.05 and 120 seconds")
    runner = CliRunner(timeout=args.timeout)
    if args.cli:
        runner.command = (args.cli,)
    serve(runner)


if __name__ == "__main__":
    main()
