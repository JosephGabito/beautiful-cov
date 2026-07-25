"""Command-line interface for beautiful-cov."""

from argparse import ArgumentParser
from pathlib import Path

from beautiful_cov.application.errors import ReportGenerationError
from beautiful_cov.application.generate_report import GenerateCoverageReport
from beautiful_cov.infrastructure.coverage_py import CoveragePyDataReader
from beautiful_cov.infrastructure.html_report import StaticHtmlReportWriter

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


def main() -> None:
    """Generate a local HTML report from existing Coverage.py data."""
    parser = _build_parser()
    args = parser.parse_args()
    generate_report = GenerateCoverageReport(
        reader=CoveragePyDataReader(),
        writer=StaticHtmlReportWriter(),
    )

    try:
        report = generate_report.execute(args.output)
    except ReportGenerationError as error:
        parser.exit(1, f"beautiful-cov: {error}\n")

    print(f"Coverage: {report.coverage.total_percentage:.1f}%")
    print(f"Report: {report.index_file}")


if __name__ == "__main__":
    main()
