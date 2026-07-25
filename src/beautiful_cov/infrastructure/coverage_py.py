"""Coverage.py adapter."""

from pathlib import Path
from tokenize import open as open_python_source

from coverage import Coverage, CoverageData
from coverage.exceptions import CoverageException

from beautiful_cov.application.errors import ReportGenerationError
from beautiful_cov.domain.coverage_report import (
    CoverageReport,
    FileCoverage,
    SourceLine,
    SourceLineStatus,
)


class CoveragePyDataReader:
    """Read measured source files using Coverage.py."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = (project_root or Path.cwd()).resolve()

    def read(self) -> CoverageReport:
        """Load existing coverage data into domain objects."""
        coverage = Coverage()

        try:
            coverage.load()
            coverage_data = coverage.get_data()
            measured_files = sorted(
                filename
                for filename in coverage_data.measured_files()
                if Path(filename).suffix == ".py"
            )
            if not measured_files:
                raise ReportGenerationError("No data to report.")

            files = tuple(
                self._read_file(
                    coverage,
                    coverage_data,
                    filename,
                )
                for filename in measured_files
            )
        except CoverageException as error:
            # Coverage.py is an infrastructure detail. Translate its exception so
            # the CLI and future callers depend only on our application contract.
            raise ReportGenerationError(str(error)) from error

        return CoverageReport(files=files)

    def _read_file(
        self,
        coverage: Coverage,
        coverage_data: CoverageData,
        filename: str,
    ) -> FileCoverage:
        """Read one measured file and give it a project-relative name."""
        _, statements, excluded, missing, _ = coverage.analysis2(filename)
        contexts_by_line = coverage_data.contexts_by_lineno(filename)
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
            source_lines=self._read_source_lines(
                filename=filename,
                statements=frozenset(statements),
                excluded=frozenset(excluded),
                missing=frozenset(missing),
                contexts_by_line=contexts_by_line,
            ),
            contexts_recorded=any(
                context.strip()
                for contexts in contexts_by_line.values()
                for context in contexts
            ),
        )

    def _read_source_lines(
        self,
        *,
        filename: str,
        statements: frozenset[int],
        excluded: frozenset[int],
        missing: frozenset[int],
        contexts_by_line: dict[int, list[str]],
    ) -> tuple[SourceLine, ...]:
        """Read Python source using its declared encoding."""
        try:
            with open_python_source(filename) as source_file:
                source = source_file.read()
        except (OSError, SyntaxError, UnicodeError):
            # Coverage totals remain useful when a measured source file has
            # moved or cannot be decoded. The renderer simply omits its link.
            return ()

        lines = source.splitlines()
        return tuple(
            SourceLine(
                number=line_number,
                text=text,
                status=self._line_status(
                    line_number,
                    statements=statements,
                    excluded=excluded,
                    missing=missing,
                ),
                test_contexts=(
                    tuple(
                        sorted(
                            {
                                self._test_name(context)
                                for context in contexts_by_line.get(line_number, [])
                                if context.strip()
                            }
                        )
                    )
                    if line_number in statements and line_number not in missing
                    else ()
                ),
            )
            for line_number, text in enumerate(lines, start=1)
        )

    def _line_status(
        self,
        line_number: int,
        *,
        statements: frozenset[int],
        excluded: frozenset[int],
        missing: frozenset[int],
    ) -> SourceLineStatus:
        """Translate Coverage.py line sets into domain language."""
        if line_number in missing:
            return SourceLineStatus.MISSING
        if line_number in statements:
            return SourceLineStatus.COVERED
        if line_number in excluded:
            return SourceLineStatus.EXCLUDED
        return SourceLineStatus.PLAIN

    def _test_name(self, context: str) -> str:
        """Remove pytest-cov phase suffixes while preserving custom contexts."""
        name, separator, phase = context.rpartition("|")
        if separator and name and phase in {"setup", "run", "teardown"}:
            return name
        return context
