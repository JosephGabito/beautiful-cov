"""Coverage results understood by beautiful-cov."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath


class CoverageStatus(str, Enum):
    """The attention level communicated by a coverage result."""

    STRONG = "strong"
    WATCH = "watch"
    CRITICAL = "critical"


def coverage_status(percentage: float) -> CoverageStatus:
    """Classify a percentage using one project-wide vocabulary."""
    if percentage < 70:
        return CoverageStatus.CRITICAL
    if percentage < 80:
        return CoverageStatus.WATCH
    return CoverageStatus.STRONG


def _coverage_percentage(statements: int, missing: int) -> float:
    """Calculate weighted statement coverage."""
    if statements == 0:
        return 100.0
    return (statements - missing) / statements * 100


@dataclass(frozen=True)
class FileCoverage:
    """Coverage results for one source file."""

    path: str
    statements: int
    missing: int

    def __post_init__(self) -> None:
        """Protect the arithmetic used throughout the report."""
        if not self.path:
            raise ValueError("File path cannot be empty.")
        path = PurePosixPath(self.path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("File path must stay inside the measured project.")
        if self.statements < 0:
            raise ValueError("Statement count cannot be negative.")
        if not 0 <= self.missing <= self.statements:
            raise ValueError("Missing count must be between 0 and the statement count.")

    @property
    def name(self) -> str:
        """Return the file name without its directory."""
        return PurePosixPath(self.path).name

    @property
    def covered(self) -> int:
        """Return the number of covered statements."""
        return self.statements - self.missing

    @property
    def percentage(self) -> float:
        """Return this file's coverage percentage."""
        return _coverage_percentage(self.statements, self.missing)

    @property
    def needs_attention(self) -> bool:
        """Return whether the file contains uncovered statements."""
        return self.missing > 0

    @property
    def status(self) -> CoverageStatus:
        """Return the file's coverage health."""
        return coverage_status(self.percentage)


@dataclass(frozen=True)
class CoverageDirectory:
    """A directory with its immediate children and aggregate coverage."""

    path: str
    directories: tuple["CoverageDirectory", ...]
    files: tuple[FileCoverage, ...]

    @property
    def name(self) -> str:
        """Return the directory name shown in navigation."""
        if not self.path:
            return "Project"
        return PurePosixPath(self.path).name

    @property
    def total_statements(self) -> int:
        """Return statements in this directory and every descendant."""
        child_statements = sum(
            directory.total_statements for directory in self.directories
        )
        return child_statements + sum(file.statements for file in self.files)

    @property
    def total_missing(self) -> int:
        """Return missing statements in this directory and every descendant."""
        child_missing = sum(directory.total_missing for directory in self.directories)
        return child_missing + sum(file.missing for file in self.files)

    @property
    def total_files(self) -> int:
        """Return measured files in this directory and every descendant."""
        child_files = sum(directory.total_files for directory in self.directories)
        return child_files + len(self.files)

    @property
    def total_percentage(self) -> float:
        """Return weighted coverage for this directory tree."""
        return _coverage_percentage(self.total_statements, self.total_missing)

    @property
    def status(self) -> CoverageStatus:
        """Return the directory's coverage health."""
        return coverage_status(self.total_percentage)

    @property
    def descendants(self) -> tuple["CoverageDirectory", ...]:
        """Return all nested directories in navigation order."""
        nested = tuple(
            descendant
            for directory in self.directories
            for descendant in directory.descendants
        )
        return self.directories + nested


@dataclass
class _DirectoryNode:
    """Mutable construction state kept private from the domain model."""

    directories: dict[str, "_DirectoryNode"]
    files: list[FileCoverage]

    @classmethod
    def empty(cls) -> "_DirectoryNode":
        """Create an empty node while building a tree."""
        return cls(directories={}, files=[])

    def freeze(self, parts: tuple[str, ...] = ()) -> CoverageDirectory:
        """Turn construction state into immutable domain objects."""
        directories = tuple(
            self.directories[name].freeze((*parts, name))
            for name in sorted(self.directories)
        )
        return CoverageDirectory(
            path="/".join(parts),
            directories=directories,
            files=tuple(sorted(self.files, key=lambda file: file.name.lower())),
        )


@dataclass(frozen=True)
class CoverageReport:
    """Coverage results for all measured source files."""

    files: tuple[FileCoverage, ...]
    _root: CoverageDirectory = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Build the immutable directory tree once for every report."""
        root = _DirectoryNode.empty()

        for file in self.files:
            parts = PurePosixPath(file.path).parts
            node = root
            for directory_name in parts[:-1]:
                node = node.directories.setdefault(
                    directory_name,
                    _DirectoryNode.empty(),
                )
            node.files.append(file)

        object.__setattr__(self, "_root", root.freeze())

    @property
    def root(self) -> CoverageDirectory:
        """Return the directory hierarchy represented by measured file paths."""
        return self._root

    @property
    def total_statements(self) -> int:
        """Return the statement count across every file."""
        return self.root.total_statements

    @property
    def total_missing(self) -> int:
        """Return the missing statement count across every file."""
        return self.root.total_missing

    @property
    def total_percentage(self) -> float:
        """Return total coverage weighted by statement count."""
        return self.root.total_percentage

    def file_count_for(self, status: CoverageStatus) -> int:
        """Count measured files in one coverage-health group."""
        return sum(file.status is status for file in self.files)
