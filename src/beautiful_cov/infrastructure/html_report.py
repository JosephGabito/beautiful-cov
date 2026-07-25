"""Static HTML report writer."""

import os
from dataclasses import dataclass
from html import escape as escape_html
from importlib.resources import files
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from jinja2 import Environment, PackageLoader, StrictUndefined, TemplateError
from markupsafe import Markup
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    _TokenType,
)

from beautiful_cov.application.errors import ReportGenerationError
from beautiful_cov.domain.coverage_report import (
    CoverageDirectory,
    CoverageReport,
    CoverageStatus,
    FileCoverage,
    SourceLine,
)

MAX_TEST_CONTEXTS_PER_LINE = 100


@dataclass(frozen=True)
class CoverageRow:
    """One directory or file shown in a coverage table."""

    name: str
    kind: str
    statements: int
    missing: int
    percentage: float
    status: str
    href: str | None
    search_text: str


@dataclass(frozen=True)
class Breadcrumb:
    """One step in directory navigation."""

    name: str
    href: str | None


@dataclass(frozen=True)
class HealthGroup:
    """One segment in the project coverage-health story."""

    label: str
    count: int
    percentage: float
    status: str


@dataclass(frozen=True)
class SourceLineView:
    """Highlighted source and bounded test evidence for one line."""

    number: int
    code: Markup
    status: str
    test_context_ids: tuple[int, ...]
    test_context_count: int
    hidden_contexts: int


class StaticHtmlReportWriter:
    """Write a browsable report with packaged templates and local assets."""

    def __init__(self) -> None:
        self._templates = Environment(
            loader=PackageLoader(
                "beautiful_cov.infrastructure",
                "templates",
            ),
            autoescape=True,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def write(self, report: CoverageReport, output_directory: Path) -> Path:
        """Write the dashboard, assets, and directory pages."""
        index_file = output_directory / "index.html"

        try:
            output_directory.mkdir(parents=True, exist_ok=True)
            self._write_assets(output_directory)
            self._write_dashboard(report, index_file, output_directory)

            for directory in report.root.descendants:
                self._write_directory(directory, output_directory)

            for file in report.files:
                if file.source_lines:
                    self._write_source_file(file, output_directory)
        except (OSError, TemplateError) as error:
            raise ReportGenerationError(
                f"Could not write the report: {error}"
            ) from error

        return index_file.resolve()

    # Page generation

    def _write_dashboard(
        self,
        report: CoverageReport,
        page_file: Path,
        output_directory: Path,
    ) -> None:
        """Write the project-level coverage story."""
        root = report.root
        project_rows = [
            self._directory_row(directory, page_file, output_directory)
            for directory in root.directories
        ]
        project_rows.extend(
            self._file_row(file, page_file, output_directory) for file in root.files
        )

        candidates = [
            directory
            for directory in root.descendants
            if directory.path.count("/") == 1 and directory.total_missing
        ]
        if not candidates:
            candidates = [
                directory for directory in root.directories if directory.total_missing
            ]
        riskiest = sorted(
            candidates,
            key=lambda directory: (
                directory.total_missing,
                directory.total_statements,
            ),
            reverse=True,
        )[:6]

        self._render(
            "dashboard.html",
            page_file,
            page_title=f"beautiful-cov · {report.total_percentage:.1f}% coverage",
            **self._shared_page_context(page_file, output_directory),
            report=report,
            report_status=root.status.value,
            health_groups=self._health_groups(report),
            risk_rows=[
                self._directory_row(directory, page_file, output_directory)
                for directory in riskiest
            ],
            project_rows=project_rows,
        )

    def _write_directory(
        self,
        directory: CoverageDirectory,
        output_directory: Path,
    ) -> None:
        """Write one drill-down page for a measured directory."""
        page_file = self._directory_page(directory.path, output_directory)
        page_file.parent.mkdir(parents=True, exist_ok=True)

        rows = [
            self._directory_row(
                child,
                page_file,
                output_directory,
                show_full_path=False,
            )
            for child in directory.directories
        ]
        rows.extend(
            self._file_row(file, page_file, output_directory)
            for file in directory.files
        )

        self._render(
            "directory.html",
            page_file,
            page_title=(
                f"{directory.path} · {directory.total_percentage:.1f}% coverage"
            ),
            **self._shared_page_context(page_file, output_directory),
            directory=directory,
            directory_status=directory.status.value,
            breadcrumbs=self._breadcrumbs(
                directory,
                page_file,
                output_directory,
            ),
            rows=rows,
        )

    def _write_source_file(
        self,
        file: FileCoverage,
        output_directory: Path,
    ) -> None:
        """Write line-by-line coverage and recorded test contexts."""
        page_file = self._file_page(file.path, output_directory)
        page_file.parent.mkdir(parents=True, exist_ok=True)
        test_contexts = file.test_contexts
        context_ids = {
            context: context_id for context_id, context in enumerate(test_contexts)
        }

        self._render(
            "source.html",
            page_file,
            page_title=f"{file.path} · {file.percentage:.1f}% coverage",
            **self._shared_page_context(page_file, output_directory),
            file=file,
            file_status=file.status.value,
            breadcrumbs=self._file_breadcrumbs(
                file,
                page_file,
                output_directory,
            ),
            source_lines=self._source_line_views(
                file.source_lines,
                context_ids,
            ),
            test_contexts=test_contexts,
            test_context_count=len(test_contexts),
        )

    def _render(self, template_name: str, page_file: Path, **context: object) -> None:
        """Render a named Jinja template into one report page."""
        template = self._templates.get_template(template_name)
        page_file.write_text(template.render(**context), encoding="utf-8")

    # View preparation

    def _shared_page_context(
        self,
        page_file: Path,
        output_directory: Path,
    ) -> dict[str, str]:
        """Return navigation and asset links shared by every page."""
        return {
            "home_href": self._href(page_file, output_directory / "index.html"),
            "stylesheet_href": self._href(
                page_file,
                output_directory / "assets" / "report.css",
            ),
            "script_href": self._href(
                page_file,
                output_directory / "assets" / "report.js",
            ),
        }

    def _directory_row(
        self,
        directory: CoverageDirectory,
        page_file: Path,
        output_directory: Path,
        *,
        show_full_path: bool = True,
    ) -> CoverageRow:
        """Prepare a navigable directory row."""
        return CoverageRow(
            name=directory.path if show_full_path else directory.name,
            kind="Directory",
            statements=directory.total_statements,
            missing=directory.total_missing,
            percentage=directory.total_percentage,
            status=directory.status.value,
            href=self._href(
                page_file,
                self._directory_page(directory.path, output_directory),
            ),
            search_text=directory.path.lower(),
        )

    def _file_row(
        self,
        file: FileCoverage,
        page_file: Path,
        output_directory: Path,
    ) -> CoverageRow:
        """Prepare a measured file row."""
        return CoverageRow(
            name=file.name,
            kind="File",
            statements=file.statements,
            missing=file.missing,
            percentage=file.percentage,
            status=file.status.value,
            href=(
                self._href(
                    page_file,
                    self._file_page(file.path, output_directory),
                )
                if file.source_lines
                else None
            ),
            search_text=file.name.lower(),
        )

    def _health_groups(self, report: CoverageReport) -> tuple[HealthGroup, ...]:
        """Prepare the three project health segments."""
        total_files = len(report.files)

        def group(label: str, status: CoverageStatus) -> HealthGroup:
            count = report.file_count_for(status)
            percentage = count / total_files * 100 if total_files else 0.0
            return HealthGroup(
                label=label,
                count=count,
                percentage=percentage,
                status=status.value,
            )

        return (
            group("≥80%", CoverageStatus.STRONG),
            group("70–79%", CoverageStatus.WATCH),
            group("<70%", CoverageStatus.CRITICAL),
        )

    def _breadcrumbs(
        self,
        directory: CoverageDirectory,
        page_file: Path,
        output_directory: Path,
    ) -> tuple[Breadcrumb, ...]:
        """Build links from the dashboard to the current directory."""
        crumbs = [
            Breadcrumb(
                name="Project",
                href=self._href(page_file, output_directory / "index.html"),
            )
        ]
        parts = PurePosixPath(directory.path).parts

        for index, part in enumerate(parts):
            path = "/".join(parts[: index + 1])
            is_current = index == len(parts) - 1
            href = None
            if not is_current:
                href = self._href(
                    page_file,
                    self._directory_page(path, output_directory),
                )
            crumbs.append(Breadcrumb(name=part, href=href))

        return tuple(crumbs)

    def _file_breadcrumbs(
        self,
        file: FileCoverage,
        page_file: Path,
        output_directory: Path,
    ) -> tuple[Breadcrumb, ...]:
        """Build links from the dashboard to one measured source file."""
        crumbs = [
            Breadcrumb(
                name="Project",
                href=self._href(page_file, output_directory / "index.html"),
            )
        ]
        parts = PurePosixPath(file.path).parts

        for index, part in enumerate(parts[:-1]):
            path = "/".join(parts[: index + 1])
            crumbs.append(
                Breadcrumb(
                    name=part,
                    href=self._href(
                        page_file,
                        self._directory_page(path, output_directory),
                    ),
                )
            )

        crumbs.append(Breadcrumb(name=file.name, href=None))
        return tuple(crumbs)

    def _source_line_views(
        self,
        lines: tuple[SourceLine, ...],
        context_ids: dict[str, int],
    ) -> tuple[SourceLineView, ...]:
        """Highlight source once while preserving line-level evidence."""
        highlighted = self._highlight_source(lines)
        return tuple(
            SourceLineView(
                number=line.number,
                code=highlighted[index],
                status=line.status.value,
                test_context_ids=tuple(
                    context_ids[context]
                    for context in line.test_contexts[:MAX_TEST_CONTEXTS_PER_LINE]
                ),
                test_context_count=len(line.test_contexts),
                hidden_contexts=max(
                    len(line.test_contexts) - MAX_TEST_CONTEXTS_PER_LINE,
                    0,
                ),
            )
            for index, line in enumerate(lines)
        )

    def _highlight_source(
        self,
        lines: tuple[SourceLine, ...],
    ) -> tuple[Markup, ...]:
        """Apply Python syntax classes without losing lexer state between lines."""
        highlighted: list[list[str]] = [[] for _ in lines]
        current_line = 0
        source = "\n".join(line.text for line in lines)
        lexer = PythonLexer(stripnl=False, ensurenl=False)

        for token_type, value in lex(source, lexer):
            parts = value.split("\n")
            css_class = self._syntax_class(token_type)

            for index, part in enumerate(parts):
                if current_line >= len(highlighted):
                    break
                escaped = escape_html(part)
                if css_class and escaped:
                    highlighted[current_line].append(
                        f'<span class="{css_class}">{escaped}</span>'
                    )
                else:
                    highlighted[current_line].append(escaped)

                if index < len(parts) - 1:
                    current_line += 1

        return tuple(Markup("".join(line)) for line in highlighted)

    def _syntax_class(self, token_type: _TokenType) -> str | None:
        """Map Pygments tokens to the small report syntax palette."""
        token_name = str(token_type)

        def matches(category: _TokenType) -> bool:
            category_name = str(category)
            return token_name == category_name or token_name.startswith(
                f"{category_name}."
            )

        if matches(Keyword):
            return "syntax-keyword"
        if matches(String):
            return "syntax-string"
        if matches(Comment):
            return "syntax-comment"
        if matches(Number):
            return "syntax-number"
        if matches(Name.Function):
            return "syntax-function"
        if matches(Name.Class):
            return "syntax-class"
        if matches(Name.Builtin):
            return "syntax-builtin"
        if matches(Operator):
            return "syntax-operator"
        if matches(Punctuation):
            return "syntax-punctuation"
        return None

    # Report filesystem

    def _write_assets(self, output_directory: Path) -> None:
        """Copy packaged CSS and JavaScript beside the generated pages."""
        asset_directory = output_directory / "assets"
        asset_directory.mkdir(parents=True, exist_ok=True)
        package = files("beautiful_cov.infrastructure").joinpath("static")

        for asset_name in ("report.css", "report.js"):
            asset = package.joinpath(asset_name)
            (asset_directory / asset_name).write_text(
                asset.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    def _directory_page(self, path: str, output_directory: Path) -> Path:
        """Return the index file assigned to one directory."""
        parts = PurePosixPath(path).parts
        return output_directory.joinpath("directories", *parts, "index.html")

    def _file_page(self, path: str, output_directory: Path) -> Path:
        """Return the HTML file assigned to one measured source file."""
        parts = PurePosixPath(path).parts
        filename = f"{parts[-1]}.html"
        return output_directory.joinpath("files", *parts[:-1], filename)

    def _href(self, current_page: Path, target: Path) -> str:
        """Return a portable URL from one generated page to another."""
        relative = Path(os.path.relpath(target, start=current_page.parent))
        return quote(relative.as_posix(), safe="/.")
