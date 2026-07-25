"""Tests for the Coverage.py adapter."""

from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from coverage.exceptions import CoverageException

from beautiful_cov.application.errors import ReportGenerationError
from beautiful_cov.infrastructure.coverage_py import CoveragePyDataReader


class CoveragePyDataReaderTests(TestCase):
    """Verify the boundary between beautiful-cov and Coverage.py."""

    @patch("beautiful_cov.infrastructure.coverage_py.Coverage")
    def test_reads_existing_coverage_data(self, coverage_class: MagicMock) -> None:
        coverage = coverage_class.return_value
        coverage.get_data.return_value.measured_files.return_value = {
            "/project/app/main.py",
            "/project/app/template.html",
        }
        coverage.analysis2.return_value = (
            "/project/app/main.py",
            [1, 2, 3, 4],
            [],
            [3],
            "3",
        )

        report = CoveragePyDataReader(project_root=Path("/project")).read()

        coverage.load.assert_called_once_with()
        coverage.analysis2.assert_called_once_with("/project/app/main.py")
        self.assertEqual(report.files[0].path, "app/main.py")
        self.assertEqual(report.files[0].statements, 4)
        self.assertEqual(report.files[0].missing, 1)

    @patch("beautiful_cov.infrastructure.coverage_py.Coverage")
    def test_translates_coverage_errors(self, coverage_class: MagicMock) -> None:
        coverage_class.return_value.load.side_effect = CoverageException(
            "No data to report."
        )

        with self.assertRaisesRegex(ReportGenerationError, "No data to report."):
            CoveragePyDataReader().read()

    @patch("beautiful_cov.infrastructure.coverage_py.Coverage")
    def test_rejects_empty_coverage_data(self, coverage_class: MagicMock) -> None:
        coverage_data = coverage_class.return_value.get_data.return_value
        coverage_data.measured_files.return_value = set()

        with self.assertRaisesRegex(ReportGenerationError, "No data to report."):
            CoveragePyDataReader().read()
