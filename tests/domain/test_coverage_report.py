"""Tests for the coverage report domain model."""

from unittest import TestCase

from beautiful_cov.domain.coverage_report import (
    CoverageReport,
    CoverageStatus,
    FileCoverage,
)


class FileCoverageTests(TestCase):
    """Protect the rules for one measured source file."""

    def test_calculates_coverage_percentage(self) -> None:
        file = FileCoverage(path="app/main.py", statements=80, missing=10)

        self.assertEqual(file.covered, 70)
        self.assertEqual(file.percentage, 87.5)
        self.assertTrue(file.needs_attention)

    def test_treats_an_empty_file_as_fully_covered(self) -> None:
        file = FileCoverage(path="app/__init__.py", statements=0, missing=0)

        self.assertEqual(file.percentage, 100.0)
        self.assertFalse(file.needs_attention)

    def test_rejects_more_missing_statements_than_total_statements(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Missing count must be between 0 and the statement count."
        ):
            FileCoverage(path="app/main.py", statements=2, missing=3)

    def test_rejects_a_path_outside_the_project(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "File path must stay inside the measured project.",
        ):
            FileCoverage(path="../outside.py", statements=2, missing=0)


class CoverageReportTests(TestCase):
    """Protect project-wide coverage calculations."""

    def test_calculates_weighted_totals(self) -> None:
        report = CoverageReport(
            files=(
                FileCoverage("app/main.py", statements=80, missing=10),
                FileCoverage("app/config.py", statements=20, missing=10),
            )
        )

        self.assertEqual(report.total_statements, 100)
        self.assertEqual(report.total_missing, 20)
        self.assertEqual(report.total_percentage, 80.0)

    def test_builds_directory_aggregates_from_file_paths(self) -> None:
        report = CoverageReport(
            files=(
                FileCoverage("app/main.py", statements=80, missing=10),
                FileCoverage("app/api/routes.py", statements=20, missing=10),
                FileCoverage("config.py", statements=10, missing=0),
            )
        )

        root = report.root
        app = root.directories[0]
        api = app.directories[0]

        self.assertEqual(root.files[0].name, "config.py")
        self.assertEqual(app.path, "app")
        self.assertEqual(app.total_statements, 100)
        self.assertEqual(app.total_missing, 20)
        self.assertEqual(app.total_files, 2)
        self.assertEqual(api.path, "app/api")
        self.assertEqual(
            tuple(directory.path for directory in root.descendants),
            ("app", "app/api"),
        )

    def test_counts_files_by_coverage_health(self) -> None:
        report = CoverageReport(
            files=(
                FileCoverage("strong.py", statements=10, missing=1),
                FileCoverage("watch.py", statements=10, missing=3),
                FileCoverage("critical.py", statements=10, missing=4),
            )
        )

        self.assertEqual(report.file_count_for(CoverageStatus.STRONG), 1)
        self.assertEqual(report.file_count_for(CoverageStatus.WATCH), 1)
        self.assertEqual(report.file_count_for(CoverageStatus.CRITICAL), 1)
