"""Tests for the beautiful-cov command-line interface."""

import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from beautiful_cov.application.errors import ReportGenerationError
from beautiful_cov.cli import main
from beautiful_cov.domain.coverage_report import CoverageReport, FileCoverage


class MainTests(TestCase):
    """Verify the public command-line behavior."""

    @patch("beautiful_cov.cli.StaticHtmlReportWriter")
    @patch("beautiful_cov.cli.CoveragePyDataReader")
    def test_main_generates_report_in_requested_directory(
        self,
        reader_class: MagicMock,
        writer_class: MagicMock,
    ) -> None:
        coverage = CoverageReport(
            files=(FileCoverage("app/main.py", statements=80, missing=10),)
        )
        expected_report = Path("custom-coverage-report", "index.html").resolve()
        writer_class.return_value.write.return_value = expected_report
        reader_class.return_value.read.return_value = coverage
        stdout = StringIO()

        with (
            patch.object(
                sys,
                "argv",
                ["beautiful-cov", "--output", "custom-coverage-report"],
            ),
            redirect_stdout(stdout),
        ):
            main()

        reader_class.return_value.read.assert_called_once_with()
        writer_class.return_value.write.assert_called_once_with(
            coverage,
            Path("custom-coverage-report"),
        )
        self.assertEqual(
            stdout.getvalue(),
            f"Coverage: 87.5%\nReport: {expected_report}\n",
        )

    @patch("beautiful_cov.cli.GenerateCoverageReport")
    def test_main_reports_coverage_errors_without_traceback(
        self, use_case_class: MagicMock
    ) -> None:
        use_case_class.return_value.execute.side_effect = ReportGenerationError(
            "No data to report."
        )
        stderr = StringIO()

        with (
            patch.object(sys, "argv", ["beautiful-cov"]),
            redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            main()

        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(
            stderr.getvalue(),
            "beautiful-cov: No data to report.\n",
        )
