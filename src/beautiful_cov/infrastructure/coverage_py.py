"""Coverage.py adapter."""

from pathlib import Path

from coverage import Coverage
from coverage.exceptions import CoverageException

from beautiful_cov.application.errors import ReportGenerationError
from beautiful_cov.domain.coverage_report import CoverageReport, FileCoverage


class CoveragePyDataReader:
    """Read measured source files using Coverage.py."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = (project_root or Path.cwd()).resolve()

    def read(self) -> CoverageReport:
        """Load existing coverage data into domain objects."""
        coverage = Coverage()

        try:
            coverage.load()
            measured_files = sorted(
                filename
                for filename in coverage.get_data().measured_files()
                if Path(filename).suffix == ".py"
            )
            if not measured_files:
                raise ReportGenerationError("No data to report.")

            files = tuple(
                self._read_file(coverage, filename) for filename in measured_files
            )
        except CoverageException as error:
            # Coverage.py is an infrastructure detail. Translate its exception so
            # the CLI and future callers depend only on our application contract.
            raise ReportGenerationError(str(error)) from error

        return CoverageReport(files=files)

    def _read_file(self, coverage: Coverage, filename: str) -> FileCoverage:
        """Read one measured file and give it a project-relative name."""
        _, statements, _, missing, _ = coverage.analysis2(filename)
        path = Path(filename)

        try:
            display_path = path.resolve().relative_to(self._project_root)
        except ValueError:
            # Keep domain paths safe and navigable even when coverage data
            # includes a measured file outside the current project root.
            display_path = Path("_external") / path.name

        return FileCoverage(
            path=display_path.as_posix(),
            statements=len(statements),
            missing=len(missing),
        )
