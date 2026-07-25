"""Contracts required by the application layer."""

from pathlib import Path
from typing import Protocol

from beautiful_cov.domain.coverage_report import CoverageReport


class CoverageDataReader(Protocol):
    """Read coverage data without exposing a coverage engine to the application."""

    def read(self) -> CoverageReport:
        """Return the coverage results for the current project."""
        ...


class CoverageReportWriter(Protocol):
    """Write a coverage report without choosing a presentation technology."""

    def write(self, report: CoverageReport, output_directory: Path) -> Path:
        """Write ``report`` and return its entry point."""
        ...
