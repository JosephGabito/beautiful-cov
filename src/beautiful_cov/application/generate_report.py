"""Generate a coverage report."""

from dataclasses import dataclass
from pathlib import Path

from beautiful_cov.application.ports import CoverageDataReader, CoverageReportWriter
from beautiful_cov.domain.coverage_report import CoverageReport


@dataclass(frozen=True)
class GeneratedReport:
    """The coverage result and the report written for it."""

    coverage: CoverageReport
    index_file: Path


class GenerateCoverageReport:
    """Coordinate coverage input and report output."""

    def __init__(
        self,
        reader: CoverageDataReader,
        writer: CoverageReportWriter,
    ) -> None:
        self._reader = reader
        self._writer = writer

    def execute(self, output_directory: Path) -> GeneratedReport:
        """Generate a report in the directory requested by the user."""
        report = self._reader.read()
        index_file = self._writer.write(report, output_directory.expanduser())
        return GeneratedReport(coverage=report, index_file=index_file)
