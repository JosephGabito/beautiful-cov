"""Failures that callers of beautiful-cov can handle."""


class ReportGenerationError(Exception):
    """The requested coverage report could not be generated."""
