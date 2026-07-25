"""Tests for the static HTML report writer."""

from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from urllib.parse import unquote

from beautiful_cov.domain.coverage_report import (
    CoverageReport,
    FileCoverage,
    SourceLine,
    SourceLineStatus,
)
from beautiful_cov.infrastructure.html_report import StaticHtmlReportWriter


class _LocalLinkCollector(HTMLParser):
    """Collect local report links without adding an HTML test dependency."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attribute_name = "src" if tag == "script" else "href"
        if tag not in {"a", "link", "script"}:
            return

        attributes = dict(attrs)
        value = attributes.get(attribute_name)
        if value:
            self.links.append(value)


class StaticHtmlReportWriterTests(TestCase):
    """Verify the portable report generated for the browser."""

    def test_writes_dashboard_assets_and_directory_navigation(self) -> None:
        report = CoverageReport(
            files=(
                FileCoverage("app/<unsafe>.py", statements=100, missing=25),
                FileCoverage("app/api/routes.py", statements=50, missing=10),
                FileCoverage("root.py", statements=10, missing=0),
            )
        )

        with TemporaryDirectory() as directory:
            output_directory = Path(directory) / "report"
            index_file = StaticHtmlReportWriter().write(report, output_directory)
            dashboard = index_file.read_text(encoding="utf-8")
            app_page = output_directory / "directories" / "app" / "index.html"
            app_html = app_page.read_text(encoding="utf-8")
            css_file = output_directory / "assets" / "report.css"
            css_exists = css_file.is_file()
            css = css_file.read_text(encoding="utf-8")
            javascript_exists = (output_directory / "assets" / "report.js").is_file()

        self.assertEqual(index_file.name, "index.html")
        self.assertIn("File coverage", dashboard)
        self.assertIn("Directories by missing lines", dashboard)
        self.assertIn("Project root", dashboard)
        self.assertIn("≥80%", dashboard)
        self.assertIn("70–79%", dashboard)
        self.assertIn("&lt;70%", dashboard)
        self.assertNotIn("Where to look", dashboard)
        self.assertNotIn(">strong<", dashboard)
        self.assertNotIn(">watch<", dashboard)
        self.assertNotIn(">critical<", dashboard)
        self.assertIn('href="directories/app/index.html"', dashboard)
        self.assertNotIn(">bc<", dashboard)
        self.assertTrue(css_exists)
        self.assertTrue(javascript_exists)
        self.assertIn(
            "grid-template-columns: minmax(240px, 20%) minmax(0, 1fr);",
            css,
        )
        self.assertIn('aria-label="Breadcrumb"', app_html)
        self.assertIn('href="../../index.html">Project</a>', app_html)
        self.assertIn("&lt;unsafe&gt;.py", app_html)
        self.assertIn('id="content-search"', app_html)

    def test_writes_pages_for_nested_directories(self) -> None:
        report = CoverageReport(
            files=(
                FileCoverage(
                    "app/application/chat/service.py",
                    statements=40,
                    missing=4,
                ),
            )
        )

        with TemporaryDirectory() as directory:
            output_directory = Path(directory) / "report"
            StaticHtmlReportWriter().write(report, output_directory)
            page = (
                output_directory
                / "directories"
                / "app"
                / "application"
                / "chat"
                / "index.html"
            )
            html = page.read_text(encoding="utf-8")

        self.assertIn('<h1 id="directory-title">chat</h1>', html)
        self.assertIn('href="../index.html">application</a>', html)
        self.assertIn('href="../../../../index.html">Project</a>', html)

    def test_every_generated_link_resolves_inside_the_report(self) -> None:
        report = CoverageReport(
            files=(
                FileCoverage("app/application/service.py", statements=40, missing=4),
                FileCoverage("root.py", statements=10, missing=0),
            )
        )

        with TemporaryDirectory() as directory:
            output_directory = Path(directory) / "report"
            StaticHtmlReportWriter().write(report, output_directory)
            broken_links: list[str] = []

            for page in output_directory.rglob("*.html"):
                collector = _LocalLinkCollector()
                collector.feed(page.read_text(encoding="utf-8"))

                for link in collector.links:
                    target = (page.parent / unquote(link)).resolve()
                    if not target.is_file():
                        broken_links.append(f"{page.name}: {link}")

        self.assertEqual(broken_links, [])

    def test_writes_source_lines_and_their_test_contexts(self) -> None:
        file = FileCoverage(
            path="app/main.py",
            statements=3,
            missing=1,
            source_lines=(
                SourceLine(
                    1,
                    "def load_value() -> int:",
                    SourceLineStatus.COVERED,
                    ("tests/test_main.py::test_load_value",),
                ),
                SourceLine(
                    2,
                    "    return 1",
                    SourceLineStatus.COVERED,
                    ("tests/test_main.py::test_load_value",),
                ),
                SourceLine(
                    3,
                    '    raise RuntimeError("missing")',
                    SourceLineStatus.MISSING,
                ),
                SourceLine(4, "    # no cover", SourceLineStatus.EXCLUDED),
            ),
            contexts_recorded=True,
        )

        with TemporaryDirectory() as directory:
            output_directory = Path(directory) / "report"
            StaticHtmlReportWriter().write(
                CoverageReport(files=(file,)),
                output_directory,
            )
            source_page = output_directory / "files" / "app" / "main.py.html"
            source_html = source_page.read_text(encoding="utf-8")
            directory_html = (
                output_directory / "directories" / "app" / "index.html"
            ).read_text(encoding="utf-8")

        self.assertIn('class="source-line source-line--covered"', source_html)
        self.assertIn('class="source-line source-line--missing"', source_html)
        self.assertIn('class="source-workspace"', source_html)
        self.assertIn('class="source-inspector"', source_html)
        self.assertIn('class="source-canvas"', source_html)
        self.assertIn("<dt>test context</dt>", source_html)
        self.assertIn("<dd>1</dd>", source_html)
        self.assertNotIn("1 test contexts", source_html)
        self.assertIn("Not covered", source_html)
        self.assertIn("tests/test_main.py::test_load_value", source_html)
        self.assertEqual(
            source_html.count("tests/test_main.py::test_load_value"),
            1,
        )
        self.assertIn('id="test-context-data"', source_html)
        self.assertIn('data-context-ids="0"', source_html)
        self.assertIn("syntax-keyword", source_html)
        self.assertIn('href="../../files/app/main.py.html"', directory_html)

    def test_explains_when_test_contexts_were_not_collected(self) -> None:
        file = FileCoverage(
            path="main.py",
            statements=1,
            missing=0,
            source_lines=(SourceLine(1, "value = 1", SourceLineStatus.COVERED),),
        )

        with TemporaryDirectory() as directory:
            output_directory = Path(directory) / "report"
            StaticHtmlReportWriter().write(
                CoverageReport(files=(file,)),
                output_directory,
            )
            html = (output_directory / "files" / "main.py.html").read_text(
                encoding="utf-8"
            )

        self.assertIn("Test contexts unavailable.", html)
        self.assertIn("pytest --cov-context=test", html)
