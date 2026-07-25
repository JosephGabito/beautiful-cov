<p align="center">
  <img width="200" alt="beautiful-cov logo — local Python coverage reports" src="https://github.com/user-attachments/assets/a51e9994-4f6a-434f-b552-3c99d78888cb" />
</p>

---

**Beautiful, local-first coverage reports for Python.**

`beautiful-cov` is a command-line tool that turns
[Coverage.py](https://coverage.readthedocs.io/) data into compact, browsable
HTML reports.

Coverage.py remains the source of truth. `beautiful-cov` focuses on the
presentation layer: clear summaries, useful visual hierarchy, and static output
that stays on your machine.

> [!IMPORTANT]
> `beautiful-cov` is in public beta. The report format and command-line
> interface may change before the first stable release.

## Why beautiful-cov?

Python already has excellent coverage measurement. What is missing is a modern
local report that feels as good to use as hosted dashboards without requiring
an account, an upload, or a service.

## Screenshots

<table>
  <tr>
    <td colspan="2">
      <img width="100%" height="auto" alt="beautiful-cov Python test coverage dashboard with project totals, file coverage distribution, and directory-level metrics" src="https://github.com/user-attachments/assets/32ff6e0e-427f-4e86-a03c-cfda6c5c46fd" />
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img width="100%" height="auto" alt="beautiful-cov Python coverage report showing 100% line coverage and pytest test attribution for a memory store module" src="https://github.com/user-attachments/assets/778accd9-6b82-4b68-bbce-2c944c049cbc" />
    </td>
    <td width="50%">
      <img width="100%" height="auto" alt="beautiful-cov source code coverage view highlighting covered, uncovered, and excluded Python lines with pytest evidence" src="https://github.com/user-attachments/assets/6e0c4640-96fb-4948-8107-1c2b88ad2853" />
    </td>
  </tr>
</table>

The project is guided by four principles:

- **Local by default.** Coverage data and source code never need to leave your
  machine.
- **Coverage.py underneath.** Measurement stays with the established Python
  coverage engine.
- **Static and portable.** Reports should open in a browser and be easy to
  archive or share.
- **Useful before decorative.** Visual polish should make uncovered code easier
  to understand, not hide it.

## Installation

`beautiful-cov` requires Python 3.10 or newer.

```bash
python -m pip install --pre beautiful-cov
```

## Usage

First, collect coverage data. With pytest-cov, enable test contexts so the
report can show exactly which tests executed each covered line:

```bash
pytest --cov --cov-context=test
```

Then generate the local HTML report:

```bash
beautiful-cov
```

```text
Coverage: 87.2%
Report: /path/to/project/beautiful-cov-report/index.html
```

By default, the report is written to `beautiful-cov-report/`. Choose another
directory with `--output`:

```bash
beautiful-cov --output coverage-report
```

Run the command from the directory containing your `.coverage` data file. The
generated report is a portable static directory: it has no hosted assets,
account, telemetry, or network dependency.

The beta report includes:

- A compact project dashboard with coverage totals and distribution
- Statement, missing-line, and file totals
- Aggregated directory coverage
- Breadcrumb navigation through the project tree
- Filtering within directory contents
- Per-directory and per-file coverage bars
- A two-column source inspector with covered, missing, and excluded states
- Exact pytest node IDs for covered lines when contexts are present
- Previous and next missing-line navigation
- A responsive layout for smaller screens

### Showing which tests covered a line

Coverage.py only records test names when context collection is enabled. With
pytest-cov, the complete workflow is:

```bash
pytest --cov --cov-context=test
beautiful-cov --output coverage-report
```

Covered source lines will show the recorded pytest node IDs. Plain Coverage.py
collection, such as `coverage run -m pytest`, is also supported, but it does
not identify the tests responsible for each covered line unless contexts are
configured separately. Reports generated without named contexts still show
covered and missing lines, with a clear collection hint instead of invented
test information.

## Architecture

The code follows a small domain-driven design. Each layer has one clear job:

- **Domain** defines a valid coverage report. It has no dependency on
  Coverage.py or the command line.
- **Application** owns the report-generation use case and the input/output ports
  it needs.
- **Infrastructure** reads Coverage.py data, writes the static HTML report, and
  translates third-party failures into errors owned by `beautiful-cov`.
- **Jinja templates** own report markup; Python prepares typed view data and
  filesystem-safe navigation.
- **CLI** is the composition root. It parses input, connects the use case to the
  infrastructure adapters, and presents the result.

The boundaries are deliberately small. Coverage input and HTML presentation can
change independently, so they use separate ports. Command-line parsing remains
at the edge and the domain has no dependency on Coverage.py or HTML.

## Planned capabilities

- Sorting and threshold filters
- Branch coverage and partial-branch annotations
- Optional Git diff coverage
- Light and dark themes
- Fully local static output

The roadmap is intentionally small. `beautiful-cov` will render coverage data;
it will not replace Coverage.py, run a hosted service, or collect telemetry.

## Development

Clone the repository and create an isolated environment:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --editable .
python -m pip install --group dev
```

Run the local command:

```bash
beautiful-cov
```

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

Generate a report for `beautiful-cov` itself:

```bash
pytest --cov=beautiful_cov --cov-context=test
beautiful-cov --output beautiful-cov-report
```

## Contributing

Focused bug reports, design feedback, and small pull requests are welcome
during the beta.

## License

`beautiful-cov` is licensed under the
[Apache License 2.0](LICENSE).

## Project status

Version `0.1.0b1` is the first public beta. It includes the command-line
interface, compact project and directory views, line-by-line source coverage,
and optional per-line pytest attribution generated from existing Coverage.py
data.
