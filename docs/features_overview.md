# MolTest Features Overview

MolTest is a command-line tool designed to enhance the experience of testing Ansible roles and collections with Molecule. Here's a breakdown of its key features:

1.  **Automated Scenario Discovery**
    *   `moltest` automatically scans your project for Molecule scenarios (defined by `molecule/<scenario-name>/molecule.yml` files).
    *   It intelligently excludes common virtual environment directories from the scan to avoid irrelevant findings.

2.  **Flexible Test Execution**
    *   **Run All:** Execute all discovered scenarios with a simple `moltest run`.
    *   **Target Specific Scenarios:** Run one or more specific scenarios using the `--scenario <name>` option. Multiple scenarios can be specified.
    *   **Keyword Filtering:** Select scenarios to run based on a keyword expression (similar to `pytest -k`) using `moltest run -k "expression"`. This allows matching against scenario IDs (e.g., `rolename:scenarioname`).
    *   **Parallel Execution:** Speed up test runs by executing scenarios in parallel using `moltest run --parallel <number_of_workers>`.
    *   **Fail Fast:** Stop the test run immediately after the first scenario failure with `moltest run --fail-fast`.
    *   **Max Failures:** Abort the test run after a specific number of failures using `moltest run --maxfail <N>`.

3.  **Results Caching & Efficient Reruns**
    *   `moltest` caches the pass/fail status, duration, and other metadata of each test scenario in a local `.moltest_cache.json` file.
    *   **Rerun Failed:** The `moltest run --rerun-failed` option intelligently reruns only those scenarios that failed in the previous execution, saving significant time during development and CI.
    *   **Cache Management:** 
        *   `moltest show-cache`: View the contents of the current test cache.
        *   `moltest clear-cache`: Delete the existing test cache.

4.  **Comprehensive Reporting**
    *   **Console Summary:** Provides a clear, colorized summary table of test results directly in the console.
    *   **JSON Reports:** Generate a machine-readable JSON report of test outcomes using `moltest run --json-report <path/to/report.json>`.
    *   **Markdown Reports:** Create a human-readable Markdown summary using `moltest run --md-report <path/to/report.md>`.
    *   **JUnit XML Reports:** Produce JUnit XML reports, commonly used by CI systems, with `moltest run --junit-xml <path/to/report.xml>`.

5.  **Output & Logging Control**
    *   **Live Output:** View the full, uncaptured output from Molecule tests in real-time using `moltest run -s` or `moltest run --capture no`. This is essential for debugging.
    *   **Output Capture Modes:** Control how stdout/stderr from Molecule is handled using `--capture [fd|tee|no]`.
    *   **Verbosity Levels:** Adjust the amount of information `moltest` itself outputs using `--verbose <0|1|2>`.
    *   **Logging:** Configure Python logging levels (`--log-level`) and optionally write logs to a file (`--log-file`).
    *   **Color Control:** Enable or disable colored console output (`--no-color`). It's automatically disabled in non-TTY environments.

6.  **Scenario & Fixture Introspection**
    *   **Collect Only:** List all discoverable scenario IDs (including parameterized variations) without actually running them using `moltest run --collect-only`.
    *   **Show Fixtures:** Display available parameter sets (fixtures) for each discovered scenario using `moltest run --fixtures`. This helps understand how scenarios might be parameterized through `moltest.params.yml` files.

7.  **Dependency & Environment Management**
    *   **Dependency Checks:** Automatically verifies the presence and minimum versions of critical dependencies like `molecule` and `ansible` before running tests.
    *   **Ansible Roles Path:** Allows specifying the `ANSIBLE_ROLES_PATH` via the `--roles-path` option.

8.  **Plugin System**
    *   `moltest` supports a plugin system that allows extending its functionality through custom Python modules.
    *   Plugins can implement various hook functions (e.g., `before_discovery`, `after_run`, `before_scenario_run`) to integrate custom logic at different stages of the test lifecycle.
    *   Plugins are discovered via Python entry points (`moltest.plugins`) or can be specified in a configuration file.

9.  **Configuration**
    *   Some aspects of `moltest` behavior can be configured via a `moltest.config.yml` (or similar) file, such_as listing plugins to load.

This list provides a comprehensive overview of MolTest's capabilities, aimed at making Molecule testing more efficient and developer-friendly.
