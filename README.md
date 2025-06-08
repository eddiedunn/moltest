# MolTest CLI

**MolTest** is a powerful command-line interface (CLI) tool designed to streamline the process of discovering, running, and managing [Molecule](https://molecule.readthedocs.io/) test scenarios for your Ansible roles and collections. It enhances the standard Molecule workflow by providing features like results caching, selective test reruns, and report generation in multiple formats.

## Purpose

The primary goal of MolTest is to improve the efficiency and user experience of testing Ansible content with Molecule. It addresses common needs such as:

*   **Batch Execution:** Run all discovered Molecule scenarios with a single command.
*   **Targeted Testing:** Easily rerun only previously failed tests, saving significant time during development and CI.
*   **Clear Reporting:** Generate human-readable (Markdown) and machine-readable (JSON or JUnit XML) reports of test outcomes.
*   **Simplified Workflow:** Provide a consistent interface for interacting with Molecule tests across different projects.
*   **CI/CD Integration:** Offer features and output formats suitable for integration into automated testing pipelines.

## Features

*   **Scenario Discovery:** Automatically finds Molecule scenarios within your project (supports `molecule/<scenario-name>/molecule.yml`).
*   **Test Execution:** Runs selected or all discovered Molecule scenarios.
*   **Results Caching:** Persists test results (pass/fail status, duration, return codes) in a local `.moltest_cache.json` file.
*   **Rerun Failed:** Supports rerunning only the scenarios that failed in the previous execution.
*   **Report Generation:** Creates detailed test reports in JSON, Markdown, and JUnit XML formats.
*   **Flexible CLI:** Offers commands to `run` tests, `clear-cache`, and `show-cache`.
*   **Collection and Fixture Listing:** Use `--collect-only` to list scenarios without running them and `--fixtures` to show available parameter sets.
*   **Dependency Checks:** Verifies the presence and minimum versions of `molecule` and `ansible`.

## Requirements

*   Python 3.8+
*   Molecule >= 4.0
*   Ansible Core >= 2.15
*   `click` (Python package, installed automatically)
*   `packaging` (Python package, installed automatically)
*   `colorama` (Python package, installed automatically)
*   `PyYAML` (Python package, used by Molecule for parsing `molecule.yml`)

## Installation

We use `pyenv` for managing Python versions and `uv` for managing virtual environments and packages.

1.  **Ensure you have the desired Python version installed with `pyenv`:**
    If you don't have the required Python version (e.g., 3.10), install it:
    ```bash
    pyenv install 3.11.12 # Or your desired version
    ```
    Set it as your local or global Python version. For project-specific versioning:
    ```bash
    cd moltest
    pyenv local 3.11.12 # Sets .python-version file
    ```

2.  **Clone the repository (if not already done):**
    ```bash
    git clone <repository_url>  # Replace with actual URL if hosted
    cd moltest # Ensure you are in the project directory where .python-version might be
    ```

3.  **Create and activate a virtual environment using `uv`:**
    `uv` will respect the Python version selected by `pyenv`.
    ```bash
    uv venv .venv # This creates a virtual environment named .venv
    source .venv/bin/activate
    ```
    (On Windows, use `.venv\Scripts\activate`)

4.  **Install MolTest in editable mode using `uv`:**
    This allows you to use the CLI directly while also being able to modify the source code.
    ```bash
    uv pip install -e .
    ```

5.  **Verify installation:**
    ```bash
    moltest --version
    ```

## Usage

MolTest commands are typically run from the root directory of your Ansible role or collection project where your `molecule/` directory resides.

### General Options

*   `moltest --version`: Show the installed version of MolTest and exit.
*   `moltest --help`: Show the main help message and exit.

### Running Tests: `moltest run`

This is the primary command for executing Molecule scenarios.

```bash
moltest run [OPTIONS]
```

**Options for `run`:**

*   `--scenario TEXT`: Specify a particular scenario name to run (e.g., `default`). If not provided, all discovered scenarios are run.
*   `-k EXPRESSION`: Filter scenarios by ID using a boolean expression (similar to pytest). Words are matched as substrings.
*   `--rerun-failed`, `--lf`, `-f`: Only run scenarios that failed in the last execution (based on the cache).
*   `--json-report [PATH]`, `-j`: Save a JSON report. Defaults to `moltest_report.json` if no path is provided.
*   `--md-report [PATH]`, `-m`: Save a Markdown report. Defaults to `moltest_report.md` if no path is provided.
*   `--junit-xml [PATH]`, `-x`: Save results in JUnit XML format. Defaults to `moltest_report.xml` if no path is provided.
*   `--roles-path [PATH]`: Directory containing Ansible roles (used for `ANSIBLE_ROLES_PATH`, default: `roles`).
*   `--capture [MODE]`: Output capture mode (`fd`, `tee`, or `no`). `-s` is shorthand for `--capture no`.
*   `--log-level TEXT`: Python logging level (e.g., `INFO`, `DEBUG`).
*   `--log-file PATH`: Optional file to write logs to.
*   `--no-color`: Disable colored output in the console. This is automatically enabled in CI environments or when stdout is not a TTY.
*   `--verbose INTEGER`: Set verbosity level (0, 1, 2). Higher numbers provide more output.
*   `--fail-fast`: Stop execution after the first failure.
*   `--maxfail INTEGER`: Abort after N failures (0 for unlimited).
*   `--collect-only`: List scenario IDs (including parameter identifiers) without running Molecule.
*   `--fixtures`: Show parameter set names for each discovered scenario and exit.
*   `--help`: Show help for the `run` command.

**Examples:**

*   Run all discovered scenarios:
    ```bash
    moltest run
    ```
*   Run only the 'default' scenario:
    ```bash
    moltest run --scenario default
    ```
*   Rerun only scenarios that failed previously:
    ```bash
    moltest run --rerun-failed
    ```
*   Filter scenarios with an expression:
    ```bash
    moltest run -k "web and not slow"
    ```
*   List scenarios without running them:
    ```bash
    moltest run --collect-only
    ```
*   Show parameter sets for each scenario:
    ```bash
    moltest run --fixtures
    ```
*   Run all scenarios and save reports to custom paths:
    ```bash
    moltest run --json-report custom_results.json --md-report custom_summary.md --junit-xml custom_results.xml
    ```
*   Disable output capturing:
    ```bash
    moltest run -v -s
    ```
*   Log debug output to a file:
    ```bash
    moltest run --log-level debug --log-file moltest.log
    ```

### Managing the Cache

MolTest uses a `.moltest_cache.json` file in the current working directory to store test results.

*   **`moltest show-cache`**: Display the contents of the current test results cache.
    ```bash
    moltest show-cache
    ```

*   **`moltest clear-cache`**: Clear (delete) the existing test results cache.
    ```bash
    moltest clear-cache
    ```

## Testing

The project uses `pytest` for running automated tests. Tests are located in the `tests/` directory.

To run all tests, ensure your virtual environment is activated, and then execute:

```bash
python -m pytest -v
```

Using `python -m pytest` is recommended as it ensures you are running the `pytest` installed within your active virtual environment, which helps avoid issues with mismatched interpreters or missing dependencies.

For more detailed testing instructions, including how to run specific tests, see the `AGENTS.md` file.

## How it Works

1.  **Discovery:** When `moltest run` is executed, it searches for `molecule/*/molecule.yml` files to identify available scenarios.
2.  **Execution:** For each scenario (or the specified one), it invokes `molecule test -s <scenario_name>`.
3.  **Caching:** The status (passed/failed), duration, and return code for each scenario are saved to `.moltest_cache.json`.
4.  **Reporting:** After execution, JSON and Markdown reports are generated summarizing the results.
5.  **`--rerun-failed`:** If this option is used, MolTest consults the cache to identify scenarios that previously failed and only runs those.

## Reporter Examples

See [docs/reporter_examples.md](docs/reporter_examples.md) for short snippets showing how to use the functions in `moltest.reporter` for colorized output and report generation.

## Plugin Hooks

MolTest can load user-defined Python modules that implement optional hook functions.
See [docs/plugin_example.md](docs/plugin_example.md) for a minimal example of how
to register a plugin and the available hook names.

## Contributing

(Details on how to contribute, coding standards, pull request process, etc., to be added.)

## License

(License information, e.g., MIT License, Apache 2.0, to be added.)
