"""Tests for the static HTML report writer."""

from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from urllib.parse import unquote

from beautiful_cov.domain.coverage_report import CoverageReport, FileCoverage
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
            css_exists = (output_directory / "assets" / "report.css").is_file()
            javascript_exists = (output_directory / "assets" / "report.js").is_file()

        self.assertEqual(index_file.name, "index.html")
        self.assertIn("Coverage health", dashboard)
        self.assertIn("Where to look", dashboard)
        self.assertIn("Project structure", dashboard)
        self.assertIn('href="directories/app/index.html"', dashboard)
        self.assertNotIn(">bc<", dashboard)
        self.assertTrue(css_exists)
        self.assertTrue(javascript_exists)
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
