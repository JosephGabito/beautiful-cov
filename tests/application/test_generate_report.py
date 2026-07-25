"""Tests for the report-generation use case."""

from pathlib import Path
from unittest import TestCase

from beautiful_cov.application.generate_report import GenerateCoverageReport
from beautiful_cov.domain.coverage_report import CoverageReport, FileCoverage


class FakeReader:
    """Return known coverage data without using Coverage.py."""

    def __init__(self, report: CoverageReport) -> None:
        self.report = report
        self.was_called = False

    def read(self) -> CoverageReport:
        self.was_called = True
        return self.report


class FakeWriter:
    """Record what the use case asks the report writer to do."""

    def __init__(self, index_file: Path) -> None:
        self.index_file = index_file
        self.report: CoverageReport | None = None
        self.output_directory: Path | None = None

    def write(self, report: CoverageReport, output_directory: Path) -> Path:
        self.report = report
        self.output_directory = output_directory
        return self.index_file


class GenerateCoverageReportTests(TestCase):
    """Verify orchestration without using Coverage.py or the filesystem."""

    def test_reads_coverage_and_writes_the_requested_report(self) -> None:
        report = CoverageReport(
            files=(FileCoverage("app/main.py", statements=10, missing=1),)
        )
        reader = FakeReader(report)
        writer = FakeWriter(Path("/tmp/report/index.html"))
        use_case = GenerateCoverageReport(reader=reader, writer=writer)

        result = use_case.execute(Path("~/coverage-report"))

        self.assertTrue(reader.was_called)
        self.assertIs(writer.report, report)
        self.assertEqual(
            writer.output_directory,
            Path("~/coverage-report").expanduser(),
        )
        self.assertIs(result.coverage, report)
        self.assertEqual(result.index_file, Path("/tmp/report/index.html"))
