"""Tests for the Coverage.py adapter."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

from coverage.exceptions import CoverageException

from beautiful_cov.application.errors import ReportGenerationError
from beautiful_cov.domain.coverage_report import SourceLineStatus
from beautiful_cov.infrastructure.coverage_py import CoveragePyDataReader


class CoveragePyDataReaderTests(TestCase):
    """Verify the boundary between beautiful-cov and Coverage.py."""

    @patch("beautiful_cov.infrastructure.coverage_py.Coverage")
    def test_reads_existing_coverage_data(self, coverage_class: MagicMock) -> None:
        coverage = coverage_class.return_value
        coverage_data = coverage.get_data.return_value

        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            source_file = project_root / "app" / "main.py"
            source_file.parent.mkdir()
            source_file.write_text(
                "value = 1\nif value:\n    print(value)\n# excluded\n",
                encoding="utf-8",
            )
            coverage_data.measured_files.return_value = {
                str(source_file),
                str(project_root / "app" / "template.html"),
            }
            coverage_data.measured_contexts.return_value = {
                "",
                "tests/test_main.py::test_value|run",
            }
            coverage_data.contexts_by_lineno.return_value = {
                1: [
                    "tests/test_main.py::test_value|setup",
                    "tests/test_main.py::test_value|run",
                ],
                2: ["tests/test_main.py::test_value|run"],
            }
            coverage.analysis2.return_value = (
                str(source_file),
                [1, 2, 3],
                [4],
                [3],
                "3",
            )

            report = CoveragePyDataReader(project_root=project_root).read()

        coverage.load.assert_called_once_with()
        coverage.analysis2.assert_called_once_with(str(source_file))
        self.assertEqual(report.files[0].path, "app/main.py")
        self.assertEqual(report.files[0].statements, 3)
        self.assertEqual(report.files[0].missing, 1)
        self.assertTrue(report.files[0].contexts_recorded)
        self.assertEqual(
            report.files[0].source_lines[0].test_contexts,
            ("tests/test_main.py::test_value",),
        )
        self.assertIs(
            report.files[0].source_lines[2].status,
            SourceLineStatus.MISSING,
        )
        self.assertIs(
            report.files[0].source_lines[3].status,
            SourceLineStatus.EXCLUDED,
        )

    @patch("beautiful_cov.infrastructure.coverage_py.Coverage")
    def test_translates_coverage_errors(self, coverage_class: MagicMock) -> None:
        coverage_class.return_value.load.side_effect = CoverageException(
            "No data to report."
        )

        with self.assertRaisesRegex(ReportGenerationError, "No data to report."):
            CoveragePyDataReader().read()

    @patch("beautiful_cov.infrastructure.coverage_py.Coverage")
    def test_marks_contexts_unavailable_per_file(
        self,
        coverage_class: MagicMock,
    ) -> None:
        coverage = coverage_class.return_value
        coverage_data = coverage.get_data.return_value

        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            source_file = project_root / "main.py"
            source_file.write_text("value = 1\n", encoding="utf-8")
            coverage_data.measured_files.return_value = {str(source_file)}
            coverage_data.measured_contexts.return_value = {
                "tests/test_other.py::test_other|run"
            }
            coverage_data.contexts_by_lineno.return_value = {1: [""]}
            coverage.analysis2.return_value = (
                str(source_file),
                [1],
                [],
                [],
                "",
            )

            report = CoveragePyDataReader(project_root=project_root).read()

        self.assertFalse(report.files[0].contexts_recorded)

    @patch("beautiful_cov.infrastructure.coverage_py.Coverage")
    def test_rejects_empty_coverage_data(self, coverage_class: MagicMock) -> None:
        coverage_data = coverage_class.return_value.get_data.return_value
        coverage_data.measured_contexts.return_value = {""}
        coverage_data.measured_files.return_value = set()

        with self.assertRaisesRegex(ReportGenerationError, "No data to report."):
            CoveragePyDataReader().read()
