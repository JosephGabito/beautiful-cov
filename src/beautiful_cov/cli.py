"""Command-line interface for beautiful-cov."""

from argparse import ArgumentParser
from pathlib import Path

from coverage import Coverage
from coverage.exceptions import CoverageException

DEFAULT_OUTPUT_DIRECTORY = Path("beautiful-cov-report")


def _build_parser() -> ArgumentParser:
    """Build the command-line parser."""
    parser = ArgumentParser(
        description="Generate a local HTML report from Coverage.py data."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Output directory (default: beautiful-cov-report)",
    )
    return parser


def _generate_report(output_directory: Path) -> tuple[float, Path]:
    """Generate the report and return its coverage total and entry point."""
    resolved_output = output_directory.expanduser()
    coverage = Coverage()
    coverage.load()
    total = coverage.html_report(directory=str(resolved_output))
    return total, (resolved_output / "index.html").resolve()


def main() -> None:
    """Generate a local HTML report from existing Coverage.py data."""
    parser = _build_parser()
    args = parser.parse_args()

    try:
        total, report = _generate_report(args.output)
    except CoverageException as error:
        parser.exit(1, f"beautiful-cov: {error}\n")

    print(f"Coverage: {total:.1f}%")
    print(f"Report: {report}")


if __name__ == "__main__":
    main()
