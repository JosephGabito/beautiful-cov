"""Tests for the beautiful-cov command-line interface."""

import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from coverage.exceptions import CoverageException

from beautiful_cov.cli import main


class MainTests(TestCase):
    """Verify the public command-line behavior."""

    @patch("beautiful_cov.cli.Coverage")
    def test_main_generates_report_in_requested_directory(
        self, coverage_class: MagicMock
    ) -> None:
        coverage = coverage_class.return_value
        coverage.html_report.return_value = 87.25
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

        coverage.load.assert_called_once_with()
        coverage.html_report.assert_called_once_with(directory="custom-coverage-report")
        expected_report = Path("custom-coverage-report", "index.html").resolve()
        self.assertEqual(
            stdout.getvalue(),
            f"Coverage: 87.2%\nReport: {expected_report}\n",
        )

    @patch("beautiful_cov.cli.Coverage")
    def test_main_reports_coverage_errors_without_traceback(
        self, coverage_class: MagicMock
    ) -> None:
        coverage_class.return_value.load.side_effect = CoverageException(
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
