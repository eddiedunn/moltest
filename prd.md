Great. I’ll refine and expand the PRD for `moltest` to reflect your clarified priorities and architectural considerations, including core platform compatibility (Mac/Linux with containers), GitHub Actions and GitLab CI support, minimal yet sufficient state persistence, and Ansible/Molecule version recommendations. I’ll also identify and prioritize only the core features essential to MVP: scenario discovery, rich test summaries, and re-running failed tests with report generation.

I’ll get back to you shortly with the updated PRD.


# Moltest – Product Requirements Document (PRD)

## Introduction and Overview

Moltest is a new command-line tool designed to streamline and enhance the testing of Ansible roles and playbooks using **Ansible Molecule**. Molecule is the de facto framework for automating Ansible tests (using ephemeral containers or VMs), but running multiple Molecule scenarios across many roles can be cumbersome. Moltest aims to simplify this by automatically discovering all Molecule scenarios in a project, executing them in one go, and providing clear feedback on the outcomes. The tool will aggregate results from all scenarios and present a concise, color-coded summary so developers can quickly identify failures. It will also support rerunning only failed scenarios to speed up iterative debugging. Moltest is intended to work on both macOS and Linux (including within containerized CI environments) and integrate smoothly with CI/CD pipelines (e.g. GitLab CI, GitHub Actions).

**Problem Statement:** Currently, developers must manually run `molecule test` for each scenario or rely on custom scripts/CI configurations to test multiple roles. There is no native Molecule command to run all scenarios at once with a unified summary, nor an easy way to only rerun previously failed tests. Additionally, when using Ansible's own `assert` modules for testing, a failure stops the run without an aggregated report of all test results, making debugging slower. Moltest will solve these issues by serving as a wrapper around Molecule that automates scenario discovery, runs tests (even if some fail, it will continue with others), and collates results in an easily digestible format. This improves developer productivity and confidence in test coverage.

**Summary of Solution:** Moltest will be a lightweight CLI (likely implemented in Python for compatibility with Molecule) that a user can run at the root of an Ansible project. It will find all Molecule scenarios (across one or multiple Ansible roles or playbook directories), execute each scenario’s tests (by calling Molecule internally), and then report which scenarios passed or failed. The output will be user-friendly: successes and failures will be clearly indicated (e.g. green for pass, red for fail) and a final **summary** will list all scenario outcomes. The tool will also generate optional report files (JSON and Markdown formats) for consumption by CI systems or for posting in code review. Moltest’s design emphasizes simplicity and minimal configuration – it should work out-of-the-box with standard Molecule scenario layouts. Persisting test results between runs (via a small cache file) will enable an “incremental mode” to rerun only failed scenarios, accelerating the edit-test cycle after fixing bugs.

## Goals and Key Features

**Core Functional Goals:**

1. **Automatic Scenario Discovery:** Moltest should automatically locate all Molecule scenarios in the project. This includes detecting `molecule` directories and scenario configurations (e.g. `molecule/<scenario_name>/molecule.yml`) across one or multiple roles. The user shouldn’t need to list scenarios manually – the tool will find them.
2. **Batch Execution of Scenarios:** The tool will run each discovered scenario’s tests sequentially (in MVP) unless specified otherwise. It should handle dozens of scenarios gracefully, running `molecule test` (or equivalent) for each scenario in turn. Even if some scenarios fail, Moltest must continue executing the remaining ones (to gather a full report of all failures).
3. **Detailed, Color-Coded Results Summary:** After running tests, Moltest will output a clear summary of results. Each scenario will be listed as **PASSED** or **FAILED**, with color-coding (e.g. green for pass, red for fail) for easy scanning. The summary might include counts (e.g. “15 scenarios run: 12 passed, 3 failed”). This gives developers immediate feedback on overall test status. (For example, a summary similar to pytest’s output or tox’s summary is desired, showing pass/fail per scenario).
4. **Re-run Failed Scenarios Only:** Moltest will support a flag (e.g. `--rerun-failed`) to run only the scenarios that failed in the previous test run. This requires remembering the last run’s results. The tool will implement a minimal persistence mechanism (such as writing the last run’s scenario statuses to a cache file) so that it knows which scenarios failed. This feature saves time during development: after fixing code, developers can retest just the failures instead of all scenarios. (This is conceptually similar to pytest’s “last-failed” rerun option, but applied at the scenario level).
5. **Report Generation (JSON, Markdown):** Moltest will be able to output test result summaries in multiple formats for integration purposes. JSON output will provide structured data (list of scenarios with their status, and possibly timestamps or durations), which can be ingested by other tools or CI pipelines. Markdown output will provide a nicely formatted report (e.g. a table or list of pass/fail results) that can be embedded in documentation or posted in merge request discussions. Users can specify output file paths for these reports via CLI options.
6. **CI/CD Integration:** The tool must integrate easily with continuous integration systems. This means:

   * **Exit Codes:** Moltest should exit with a non-zero status if any scenario failed (so CI jobs can detect failure). Conversely, exit 0 if all scenarios passed.
   * **Logging:** It should print human-readable output to the console (which becomes CI job log) with clear indicators of failures. The color output should be optional or auto-detected (with an option like `--no-color` for CI environments that don’t render ANSI colors).
   * **Artifacts:** The JSON/Markdown reports can be saved as CI artifacts. For example, in GitLab CI one might use `moltest --json-report results.json --md-report results.md` and then upload those files for later viewing. In GitHub Actions, a step could archive or display the Markdown summary.
   * **Ease of Use:** Ideally, minimal setup is required in CI. If Moltest is published to PyPI, it can be installed in a pipeline job and run. Alternatively, providing a Docker image with Moltest (and Molecule/Ansible) pre-installed could be considered for convenience (not strictly MVP, but an option to ease CI usage).
7. **Compatibility with Ansible Core 2.15:** Ensure that Moltest runs tests using Ansible Core 2.15 without issues. This implies using a Molecule version that supports Ansible 2.15. (Molecule traditionally supports the latest two major Ansible versions, so we will target the current Molecule release that is compatible with Ansible Core 2.15). As part of this goal, the PRD should recommend which versions of Molecule and Ansible to use. For example, if Ansible Core 2.15 corresponds to the community Ansible 2.15.x, the recommended Molecule version might be Molecule 4.x or the latest available (e.g. Molecule v25.x as per the new versioning) that supports it. We will validate Moltest with Ansible Core 2.15 and likely also ensure forward-compatibility with the next Ansible release (since Molecule will evolve to support Ansible 2.16+ as well).

**Non-Functional Goals:**

1. **Cross-Platform Support (macOS/Linux containers):** Moltest must run seamlessly on macOS and Linux environments. This includes running inside containerized environments (e.g. Docker containers) since many CI systems use Linux containers for jobs. No functionality should be OS-specific; any paths or shell commands used must be portable. We assume Windows support is not required (out of scope for MVP, unless running under WSL), focusing on Unix-like systems which Molecule itself supports (Molecule is tested on POSIX and macOS platforms).
2. **Performance:** The tool should add minimal overhead on top of Molecule’s own execution time. Running scenarios in sequence means total time is sum of each scenario’s time; this is acceptable for MVP. We will ensure Moltest itself starts quickly and can handle output streaming efficiently. In future, we may explore parallel execution to speed up large test suites (not in MVP due to complexity and Molecule’s experimental parallel support).
3. **Reliability and Robustness:** Moltest should handle failures gracefully. If a scenario fails (e.g. Molecule returns a non-zero exit), Moltest should record it and continue with the next scenario, rather than aborting the entire run. It should also properly clean up or delegate cleanup to Molecule (Molecule usually destroys instances even on failure). The summary and exit code logic must reliably reflect the test outcomes. Additionally, the persistence of results (cache file) should not corrupt or falsely skip tests – it must be updated atomically and have a way to reset (perhaps an option to clear the cache or always treat missing cache as “no tests failed previously”).
4. **Minimal Dependencies & Installation:** The tool should be easy to install (pip installable) and not require heavy dependencies beyond Molecule and Ansible. Ideally, it can be distributed as part of a dev tools package or standalone. It will use standard libraries or well-established ones for color output (e.g. Python’s `colorama` or `rich`) to ensure wide compatibility.
5. **Security Considerations:** Since this is a developer tool running local Molecule tests, there are no special security requirements beyond those of Molecule/Ansible (which execute playbooks on test instances). Moltest will not transmit data externally; all reports are local files. We will ensure any temporary files (like the results cache) are stored in the project or user’s directory, not in insecure system locations.

## User Stories

To clarify the requirements, here are key user stories for Moltest:

* **(Batch Testing)** *As an Ansible role developer or DevOps engineer with many roles and scenarios,* I want to run **all Molecule scenarios with a single command**, so that I can verify my entire project’s infrastructure code without manually running each scenario.
* **(Result Visibility)** *As a developer running Molecule tests,* I want the tool to provide a **clear summary of which scenarios passed or failed**, color-coded for quick reading, so that I can immediately identify problem areas after a test run.
* **(Failure Focus)** *As a developer who is fixing a broken role,* I want to **re-run only the failed Molecule scenarios from the last run**, so that I can save time and confirm my fixes without re-executing tests that already passed.
* **(CI Integration)** *As a CI/CD engineer,* I want Moltest to **integrate easily into GitLab CI or GitHub Actions**, so that I can automate Ansible role testing in the pipeline. This means it should run headlessly in a Linux container, use appropriate exit codes to signal success/failure, and allow exporting results (e.g. as JSON/Markdown) for pipeline artifacts or comments.
* **(Consistency Across Environments)** *As a developer using both macOS for local development and Linux containers in CI,* I need Moltest to **work consistently on both platforms** (and in containerized runtime), so that “it works on my machine” and CI yield the same outcomes and I don’t have environment-specific test issues.
* **(Guidance on Versions)** *As a project maintainer or team lead,* I want to know **which versions of Ansible Core and Molecule are recommended** to use with Moltest, so that our team is using a tested, compatible toolchain. (For example, if we are on Ansible Core 2.15, I’d like to know the appropriate Molecule version that Moltest has been validated against, to avoid any version mismatch problems.)
* **(Extendability – Future)** *As an advanced user (future scenario),* I may want to **extend or hook into Moltest’s workflow** – for example, to run custom scripts before/after each scenario or to add custom result processors. While this is not needed in the first release, having a plugin/hook system in a future version would let power users customize the tool for their organization’s needs. *(This is a backlog consideration, acknowledging future extensibility.)*

## Functional Requirements

**1. Scenario Discovery:** Moltest shall search the project for Molecule scenarios automatically. By default, when run in the root of an Ansible repository, it should find all subdirectories named `molecule/*` that contain a `molecule.yml` (Molecule config). This includes:

* Single-role repositories: e.g. a `molecule/` directory with sub-folders per scenario (like `molecule/default/`, `molecule/<other_scenario>/`). Moltest should detect each scenario folder.
* Multi-role repositories or Ansible Collections: Moltest should find molecule scenarios in each role. For instance, if roles are in a `roles/` directory, it should scan each `roles/<role_name>/molecule/*/molecule.yml`. Similarly, if testing playbooks, scenarios might be defined in a `molecule/` folder at repository root.
* The discovery mechanism can be a simple filesystem search (glob) for `molecule.yml` files. Each found file defines a scenario; the scenario name can be derived from the folder name (parent folder of molecule.yml).

*Edge cases:* It should avoid picking up irrelevant files named molecule.yml outside the intended structure. Possibly limit search depth or verify the directory structure matches Molecule’s expected layout.

**2. Test Execution:** For each discovered scenario, Moltest will run the Molecule test sequence. This is typically equivalent to executing `molecule test -s <scenario_name>` in the appropriate directory. To ensure Molecule runs in the correct context, Moltest may need to change the working directory to the role or project folder that contains the `molecule/` directory before invoking Molecule. The tool can invoke Molecule via a subprocess call. (It will require Molecule to be installed in the environment. We assume the user has Molecule available, or Moltest can have it as a dependency.)

* The execution should be done one scenario at a time (sequentially) in the MVP. This avoids concurrency issues and simplifies output handling. If one scenario is running, others wait until it’s done.
* If a scenario’s test fails (Molecule returns a non-zero exit code), Moltest should record that failure but continue to the next scenario. It should not abort the entire run on first failure – the goal is to report *all* failures at the end.
* Moltest should capture each scenario’s result (pass/fail) and possibly the execution time. It can do this by noting the exit code of the Molecule command and timing the duration. Any error output from Molecule should still be shown to the user in real-time (so that if a failure happens, the user sees the Molecule logs for debugging). Moltest doesn’t need to suppress Molecule’s output; rather, it can stream it. However, to keep the final summary clean, Moltest might want to reduce verbose output unless a `--verbose` flag is given. (Perhaps by default show Molecule’s standard output with minimal verbosity, but allow an option to show full detail for troubleshooting.)

**3. Result Aggregation and Color-Coded Summary:** After running all scenarios, Moltest will output a summary. This summary should list each scenario and its outcome. For example:

```text
Summary of Molecule test results:
✓ role1 (default scenario) — PASSED
✗ role1 (upgrade scenario) — FAILED
✓ role2 (default scenario) — PASSED
... etc ...
```

In the above, green **✓** (checkmark) or “PASSED” text could indicate success, and red **✗** or “FAILED” indicates failure. The summary should be visually clear, using color highlighting for pass/fail. If color is not supported (or turned off), use clear text labels like “PASSED”/“FAILED”. Additionally, provide totals at the end, e.g. **“Total: 5 passed, 2 failed, 7 scenarios run.”**

* **Color output**: Use ANSI color codes or a library for coloring. Auto-detect if the output is a TTY. Provide `--no-color` option to disable colors (for plain text logs in CI).
* The summary should come **after** all Molecule output, so it’s the last thing the user sees. This ensures that even if Molecule logs are lengthy, the user can scroll to bottom for the quick status of each scenario.
* If feasible, Moltest might also highlight failed scenario names earlier. For instance, after each scenario finishes, it could print a one-liner result (immediately indicating pass/fail) to keep a running tally, and then repeat the summary at end. This way, in a long run, the user doesn’t have to wait until the end to know which ones failed. (E.g. as soon as a scenario completes: “Scenario X: **FAILED** (exit code 1)” in red).

**4. Rerun Failed Scenarios (Persistent State):** Moltest will implement a minimal persistence mechanism to support rerunning only failed scenarios. After each run, the tool will save the results (at least the list of failed scenario identifiers, possibly all scenario statuses) to a file in the project. For example, it might create a file like `.moltest_results.json` or `.moltest_cache` in the current directory. This file can store a JSON object or similar mapping scenario names (or unique identifiers) to their last run status.

* The **`--rerun-failed`** flag (and alias `--lf` perhaps) will trigger Moltest to skip scenarios that were last recorded as “passed” and only run those that were recorded as “failed” (or potentially those not run before). If no previous results file is found, Moltest should either run all scenarios (default behavior) or warn the user that no prior run info is available. If the previous run had all tests passing, using `--rerun-failed` would result in nothing to run (Moltest can output “No previously failed scenarios to run.” and exit with code 0).
* After the rerun (or any run), the persistence file should be updated with the latest results. In an incremental workflow, a developer might do a full run, get some failures, then repeatedly use `moltest --rerun-failed` as they fix issues until all scenarios pass. At that point, the cache would mark them all passed.
* This persistence should be **reliable but minimal**: likely just a local file. We do not plan a database or complex state. The file format could be JSON for human-readability and easy parsing. For instance:

  ```json
  {
    "role1:default": "passed",
    "role1:upgrade": "failed",
    "role2:default": "passed"
  }
  ```

  Here a key might combine role and scenario name to be unique. Alternatively, store as a list of failed scenario identifiers. We need to be careful with scenario identification if multiple roles have scenarios with the same name (e.g. each role has a “default” scenario). Including the role or path in the ID is important.
* **In CI environments**, this caching is typically not reused between pipeline runs (since each run is fresh), so `--rerun-failed` is mainly a developer productivity feature locally. However, if desired, CI could cache the `.moltest_results.json` between jobs or runs to enable an incremental approach in long-running test suites (this would be an advanced use case).
* Moltest should also provide a way to **clear or ignore** the cached results if needed. Perhaps a flag `--clear-cache` to reset (or the user can manually delete the file). If the code or scenarios changed significantly, a fresh run might be needed; the tool could detect if the cache file’s format is incompatible with current project (version it, etc.).

**5. Reporting in Multiple Formats:** In addition to console output, Moltest will support generating reports:

* **JSON Report:** A structured report of the test outcomes. This JSON could include an array of scenarios with details like name, status, duration, perhaps the path, and a timestamp of the run. This is useful for programmatic processing. (For example, a CI pipeline could read this JSON to decide next steps or to upload results to a dashboard). We might call this via an option like `--json-report <filepath>`.

* **Markdown Report:** A human-friendly report intended to be viewed in Markdown (e.g. in a Merge Request description or an issue comment). This could be a table or bullet list of scenarios and their results. For example:

  | Scenario        | Status |
  | --------------- | ------ |
  | role1 – default | ✅ Pass |
  | role1 – upgrade | ❌ Fail |
  | role2 – default | ✅ Pass |

  or, a bulleted list:

  * **role1/default:** **Pass**
  * **role1/upgrade:** **Fail** – (error details…)
  * **role2/default:** **Pass**

  The Markdown can use emojis or bold text to highlight pass/fail. This report can be saved to a file via an option like `--md-report <filepath>`.

* The content of the reports should mirror the summary information. Optionally, we might include a bit more detail (for example, if a scenario failed, maybe include a one-line snippet of the error or a link to full log). However, including full logs in Markdown might be too heavy; that could be a later enhancement. MVP will focus on status only.

* If neither option is provided, no report files are generated (just console output). If options are given, Moltest writes the files after running all tests.

**6. CI Integration Details:** The design of Moltest inherently supports CI usage, but some specifics to note (some overlap with earlier points):

* Running `moltest` in a CI job should require minimal setup. Ideally: ensure Python, Ansible, and Molecule are installed, then install Moltest (via pip or use a container that has it). Then simply invoke `moltest`.
* **GitLab CI:** In GitLab, one could use a Python image or custom image with Ansible/Molecule. A job script might be:

  ```yaml
  test:
    image: python:3.11
    script:
      - pip install ansible-core==2.15 molecule==<version> moltest==<version>
      - moltest --json-report results.json --md-report results.md
    artifacts:
      paths:
        - results.json
        - results.md
  ```

  This would run all tests and save the reports. The Markdown could even be used with the GitLab “\$CI\_MERGE\_REQUEST\_IID” via the API to comment on an MR (future automation idea).
* **GitHub Actions:** Similarly, use `uses: actions/setup-python` to get Python, install dependencies, run moltest. The JSON/MD can be uploaded with `actions/upload-artifact` for later download. Or use `actions/upload-artifact` to collect logs as needed.
* Moltest should be aware if it’s running in a non-interactive environment. For example, it might default `--no-color` if it detects `CI=true` environment variable or no TTY, to avoid noisy ANSI codes in logs. (This is a polish item; user can also explicitly set `--no-color` in CI).
* The exit code behavior is crucial: if any scenario fails, Moltest exits with code 1 (or some non-zero). If all pass, exit 0. This way CI will mark the job as failed on any test failure, which is the expected behavior. There could be an option like `--continue-on-fail` to always exit 0 for special cases, but by default we want strict failure signaling.

**7. Compatibility and Version Support:**

* **Ansible Core 2.15:** Moltest must be fully compatible with Ansible Core 2.15. This means it should be able to run Molecule scenarios that use Ansible Core 2.15 as the execution engine. Any deprecations or changes in Ansible 2.15 (compared to earlier versions) that affect Molecule should be accounted for. For instance, if certain syntax or plugin behaviors changed in 2.15, Moltest itself is mostly agnostic (since it delegates to Molecule), but we will test Moltest in an environment with Ansible 2.15 to ensure everything works.
* **Molecule Version:** We will target the latest stable Molecule release that supports Ansible 2.15. As of mid-2025, Molecule’s versioning has shifted (e.g. a release v25.5.0 in May 2025). For clarity, we recommend using Molecule v4 or higher (essentially the version included in the Ansible Developer Tools package around Ansible 2.15 timeframe). The Molecule project states it supports only the two latest Ansible major versions, so using an updated Molecule is advised. (If Ansible 2.15 is current, Molecule likely supports 2.15 and 2.14; older Molecule might not support 2.15 features).
* **Recommended Combination:** The PRD recommends using **Ansible Core 2.15** with **Molecule >= 4.x** (or the equivalent latest release, which could be installed via `pip install ansible-core==2.15 molecule` or `ansible-dev-tools`). We will validate Moltest on that combination. As new Ansible versions come out (2.16, 2.17, etc.), Moltest should remain compatible as long as Molecule is updated. We plan to track Molecule/Ansible development to ensure compatibility (e.g., Molecule adding support for Ansible 2.16, 2.17 – Moltest should work with those as well, possibly requiring minor updates if any breaking changes occur).
* We should document the environment requirements: Python 3.10+ (since Molecule requires Python ≥3.10) and the installed versions of Ansible/Molecule. Moltest itself will specify these as dependencies or at least check versions at runtime to warn if incompatible versions are detected (nice-to-have: e.g., if user’s ansible-core is too old or Molecule is outdated, print a warning).

**8. Minimal Persistency for Incremental Runs:**
*(This reiterates some points from #4, focusing on reliability.)*

* The caching of test outcomes should be implemented in a **simple, robust way**. For example, writing to a JSON file in one go after the test suite finishes (to avoid partial writes if interrupted).
* The cache file (say `.moltest_cache.json`) should be small and easily parseable. We might include in it a timestamp or Moltest version, so that if format changes we can invalidate old cache.
* Only basic information is stored (scenario identifiers and pass/fail status). We deliberately avoid storing excessive data or logs in this file, to keep it lightweight.
* Concurrency: Since MVP runs tests sequentially, we don’t have to worry about concurrent writes to the cache. If in future we allow parallel runs, we’ll have to consider thread-safe or process-safe writes (perhaps each parallel job writes a temp file and Moltest merges them). But for now, one run at a time updates the file.
* **Security/Integrity:** If the file is manually edited or corrupted, Moltest should handle it (e.g., if JSON parse fails, we ignore the cache and run all tests, maybe issuing a notice).

## Technical Architecture

**Overall Architecture:** Moltest will be a CLI tool likely written in Python. Internally, it will function as a orchestrator that glues together Molecule invocations and result processing. Here are the main components/modules in the architecture:

* **CLI Interface & Command Parser:** Using Python’s argparse or a library like Click/Typer, Moltest will parse command-line arguments (options like `--rerun-failed`, `--json-report`, etc.). This module will trigger the appropriate high-level commands (for MVP, essentially one main command: “run tests”). In the future, if needed, we could have subcommands (e.g., `moltest run`, `moltest list` to just list scenarios, etc., but not strictly necessary in MVP).
* **Scenario Discovery Module:** This component handles scanning the filesystem for Molecule scenarios. It might use `os.walk` or `glob` patterns. For each discovered scenario, it will record:

  * a **name** (possibly in format `<role>/<scenario>` or `<scenario>` if single-role context),
  * the **path** to the scenario’s directory (which contains molecule.yml),
  * the **base directory** from which to run Molecule. For a role, this is usually the role’s root (one level above the `molecule/` folder) because running `molecule` inside the role directory ensures Molecule picks up the role correctly. In a single playbook repository scenario, the base dir might be the repository root.
    The discovery could also consider reading Molecule’s own configuration if available, but likely unnecessary; a simple filesystem approach is sufficient.
* **Executor Module:** Responsible for running a Molecule test for a given scenario. This will likely use Python’s `subprocess.run` to call `molecule`. (Alternatively, we could explore using Molecule’s API directly, but Molecule is primarily a CLI tool; using its API might not be stable or documented. Using the CLI ensures we’re doing exactly what a user would do manually.)

  * The executor will take a scenario (from the discovery module) and run `molecule test -s <name>` in the appropriate directory. We will pass `--parallel` flag if we decide to run scenarios concurrently (not in MVP, unless a simple sequential parallelism for different roles is trivial – but likely skip for now).
  * We should ensure environment variables like `ANSIBLE_CORE` or other Molecule context are properly set if needed. Typically, if Molecule is installed, running it is enough. Molecule will use the local Ansible (which we have ensured is 2.15). No special env is needed unless the user’s scenario expects something (e.g. cloud credentials), which is outside Moltest’s scope.
  * The executor can capture the return code and stdout/stderr. It might not need to store all output in memory (could stream to console). For summarizing, only the final status is needed and maybe the last few lines of output if we want to report a reason for failure. For MVP, we might not analyze logs; just status.
  * If a scenario times out or hangs, Moltest might need a timeout mechanism (this is advanced; possibly let Molecule’s own timeouts handle it if any, or allow user to interrupt). We should ensure Ctrl+C (keyboard interrupt) is handled to terminate any running Molecule child process gracefully.
* **Result Collection and Formatting:** As each scenario finishes, Moltest adds an entry to a results list in memory. This entry might include scenario identifier, status (pass/fail), and maybe duration. After all are done, this module is responsible for generating the summary output and any report files. This includes applying colors for console, formatting Markdown table, writing JSON, etc.

  * We could use a library like `rich` to simplify colored console output and even tables. But to keep dependencies minimal, manual ANSI codes via `print` could suffice (e.g. `print(f"\x1b[32mPASS\x1b[0m")` for green text). Colorama could be used on Windows to enable ANSI, but we target Linux/macOS primarily.
  * JSON writing can be done with Python’s json module (dumps to file). Markdown can be built manually as a string. No heavy library needed for those.
* **Persistence (Cache) Handler:** A small module that reads/writes the cache file for last results. On start, if `--rerun-failed` is requested, this module provides the list of scenarios to run (by comparing stored results). On finish, it writes the new results. We must decide on the file location – likely the current working directory (project root) as `.moltest.json` or similar. (Alternatively, could use `~/.cache/moltest/` in user home for a more global cache, but that might mix results from different projects, which is not ideal. Better to keep per project in the project dir.)

  * The cache file format, as discussed, will be JSON mapping scenario IDs to status. We should include the Moltest version and maybe a timestamp. Example:

    ```json
    {
      "moltest_version": "1.0.0",
      "last_run": "2025-07-01T15:30:00Z",
      "scenarios": {
         "role1:default": "passed",
         "role1:upgrade": "failed",
         "playbookX:centos7": "passed"
      }
    }
    ```

    The scenario key can be `"role:scenario"` for roles, or `"scenario"` for top-level scenarios (or include path to avoid collision).
  * On `--rerun-failed`, Moltest will filter the discovered scenario list to only those with status "failed" in the cache. If a scenario is newly added or not in cache, we might consider it as "not run before" which could either be treated as failed (to ensure it gets run) or just inform user. Simpler: treat unknown scenarios as needing to run (especially if user added a new scenario, they’d want it tested).

**Error Handling & Edge Cases:**

* If Molecule is not installed or not found, Moltest should detect this and give a friendly error (e.g. “Molecule is not installed or not in PATH. Please install Ansible Molecule before running moltest.”). Since Moltest heavily relies on Molecule, this check is important. We might list Molecule as a dependency in setup (so pip installing Moltest also pulls Molecule), but we need to ensure compatibility with the user’s Ansible version. Possibly we specify `molecule>=X` in requirements.
* If no scenarios are found, Moltest should output “No Molecule scenarios found.” and exit 0 (since nothing to test, arguably not an error condition, but perhaps we exit with a special code or 0).
* If a scenario discovery or execution fails due to unexpected reasons (e.g. a broken molecule.yml), Molecule itself will likely throw an error. Moltest can catch non-zero exit and mark it failed. That’s fine.
* If the results cache file cannot be written (disk issue, permission), Moltest should warn but not crash. The cache is a convenience; tests still ran. So it can say “Warning: could not write cache file, incremental reruns may not work.”
* **Integration with Molecule internals:** Molecule now has some advanced features like `--parallel` (which uses a special caching in `~/.cache/molecule_parallel` for docker driver). In MVP we won’t use `--parallel` by default, but it’s good to know: if in future we allow parallel execution (e.g. run 2 scenarios simultaneously to cut time), we should leverage `molecule --parallel` to avoid conflicts. This is a future consideration; we note it in backlog.
* **Plugin/Hook System (Future Architecture):** Although not in MVP, it’s worth envisioning how a plugin architecture might fit. Likely, we would design Moltest to have hook points around key events (before running a scenario, after a scenario, before all tests, after all tests, etc.). A plugin system could allow custom code to run at those points (for example, sending a Slack notification on failure, or custom parsing of results). This might involve using Python entry points or a simple plugin loader that looks for modules in a `moltest_plugins` namespace. We will defer the implementation, but we keep the architecture open to extension – e.g. by not tightly coupling all logic, and possibly by documenting internal APIs if needed for plugins.

## CLI Design and Usage

The Moltest CLI will be designed for simplicity, following common conventions of command-line test tools:

* **Command Invocation:** The primary way to use the tool is by running `moltest` in the root of your project. (If installed via pip, `moltest` will be an entry point executable.)

  * Example: running `moltest` (with no arguments) will discover all scenarios and run them all.

* **Options:** Key CLI options to include in MVP:

  * `-f, --rerun-failed` – as described, run only scenarios that failed in the last run (if any). Alias `--lf` might be added for familiarity with pytest users.
  * `-j, --json-report <path>` – output the JSON report to the specified file. e.g. `moltest -j moltest_results.json`. If the file exists, it will be overwritten.
  * `-m, --md-report <path>` – output the Markdown report to a file. e.g. `--md-report results.md`. Overwritten if exists.
  * `--no-color` – disable colored output in the console summary (useful for CI logs or if the console doesn’t support ANSI).
  * `-v, --verbose` – increase verbosity. By default, Moltest might suppress some of Molecule’s internal output for brevity, but with `--verbose` it could show the full Molecule logs in real-time. This helps when debugging a failing scenario (you’d see all the Ansible output, etc.). We could even allow `-v -v` for extra verbosity if needed.
  * `--version` – show the Moltest version (standard practice). Possibly also show the versions of Ansible and Molecule it detects, which is a nice addition (for debugging environment issues). For example, `moltest --version` could output “Moltest 1.0.0, Molecule 4.0.2, Ansible Core 2.15.1”.
  * `--help` – standard help message explaining usage and options.

* **Potential Additional Options (MVP if time permits, otherwise backlog):**

  * `-s, --scenario <name>` – to run a specific scenario by name. If provided, Moltest would run only that scenario (or that scenario in each role if name overlaps? This might be tricky in multi-role context). This is somewhat redundant because a user could just run `molecule test -s name` themselves. The value-add of Moltest is running all scenarios. So this might not be necessary initially.
  * `-r, --role <role_name>` – if one wanted to run all scenarios of a specific role in a multi-role repo, perhaps. Again, could be a nice-to-have for filtering, but not core.
  * `--fail-fast` – opposite of default behavior: if set, Moltest would stop on the first failure. By default we won’t do that, but such an option might be requested by some (backlog item).
  * `--parallel N` – run N scenarios in parallel. This is definitely a future enhancement (backlog) since we’d need to manage concurrency. Possibly rely on Molecule’s own `--parallel` or simply spin multiple subprocesses. Not in MVP due to complexity.

* **Examples of CLI usage:**

  * **Basic usage:**

    ```bash
    $ moltest
    ```

    This runs all scenarios. Output might be:
    *(Moltest discovers 5 scenarios and runs them...)*

    ```
    Running scenario: role1 default
    ... [Molecule output] ...
    Scenario "role1 default" PASSED ✅

    Running scenario: role1 upgrade
    ... [Molecule output] ...
    Scenario "role1 upgrade" FAILED ❌

    ... (other scenarios) ...

    =============================
    Moltest Summary:
    5 scenarios run, 4 passed, 1 failed
    - role1/default: PASS
    - role1/upgrade: FAIL
    - role2/default: PASS
    - role2/alt: PASS
    - playbook_test: PASS
    (See results.json for details)
    ```

    In the above hypothetical output, the summary clearly shows one failure. Moltest would exit with code 1 because there was a failure. It also references results.json if the user had requested a JSON report.
  * **Rerun failed only:**

    ```bash
    $ moltest --rerun-failed
    ```

    Suppose prior run had that one failure in `role1/upgrade`. Moltest reads cache and finds only that scenario marked failed, so it runs just that one:

    ```
    Running scenario: role1 upgrade
    ... [Molecule output] ...
    Scenario "role1 upgrade" PASSED ✅

    =============================
    Moltest Summary:
    1 scenario run, 1 passed, 0 failed
    ```

    Now all scenarios pass, Moltest updates the cache and exits 0.
  * **With reports and no color (CI example):**

    ```bash
    moltest -j results.json -m results.md --no-color
    ```

    This will produce the same testing behavior, but the console output won’t have color codes (just plain text “PASS/FAIL”). The file `results.json` will contain JSON data, and `results.md` will contain a Markdown summary table. These can be inspected or uploaded by CI.

* **CLI Design considerations:** We want the interface to be intuitive for users familiar with test runners. The default behavior (no args) does the most common action (run all tests). Additional flags mirror common test tool flags (`--verbose`, `--no-color`, `--version`, etc.). We will include helpful messages: e.g., if `--rerun-failed` is used but no cache exists, Moltest will inform the user “No previous run data found; running all scenarios.” rather than silently doing nothing. If reports are generated, after running we might print a message like “Reports saved: results.json, results.md” for clarity.

## MVP Scope vs Backlog Features

It’s important to distinguish what will be delivered in the **Minimum Viable Product (MVP)** and what features are planned for future iterations (backlog).

**MVP Features (Must-have for initial release):**

* **Automatic discovery** of Molecule scenarios and sequential execution of all discovered tests.
* **Result summary** printed to console with clear pass/fail indicators (colored output).
* **Accurate exit code** reflecting overall success/failure (any failure yields non-zero).
* **Basic persistence** of last run results to support a `--rerun-failed` option. The ability to rerun only failed scenarios from last run is a key differentiator, so this is included in MVP with a simple implementation (single file cache).
* **JSON and Markdown report generation** as optional outputs. This is important for integration, so we include it in MVP. (If time were short, we might drop Markdown or JSON, but these are straightforward to implement and highly useful, so we plan to deliver both formats).
* **Compatibility assurances**: Test and support with Ansible Core 2.15 and the corresponding Molecule version. Document the recommended versions. The tool should ideally enforce or check these versions (e.g. require Molecule version >= X).
* **CI-friendly behavior**: although not a separate feature, ensuring the tool works in CI (no interactive prompts, no assumptions of TTY, an option for no-color, etc.) is part of MVP quality.
* **Documentation**: As part of MVP, we will provide a README or user guide on how to install and use Moltest, with examples (including CI integration examples). Also, documentation on the output formats and any configuration (if needed) will be included.

**Backlog / Future Enhancements:**

* **Plugin/Hook Architecture:** The ability to extend Moltest via plugins is a planned feature post-MVP. This could allow users to add custom logic at various points (e.g., custom notifications, integrating additional linters or metrics after scenarios). The design might involve a plugin interface or loading external Python modules. This is complex and not needed for core functionality, so it is deferred.
* **Parallel Execution of Scenarios:** To speed up testing, especially with many scenarios, future versions might run multiple scenarios in parallel (if resources allow). Molecule has an experimental `--parallel` for the `test` sequence (limited to Docker driver). We could leverage that or manage parallel processes ourselves. This requires careful handling of output and avoiding interference (Molecule can run in parallel if given a unique UUID per run, which it does internally). We will consider adding a `--parallel` flag to Moltest in the future once stability of parallel mode is proven.
* **Selective Test Execution (Filtering):** Additional CLI options to filter which tests to run (by scenario name pattern, by role, etc.) could be added later. For example, `moltest --scenarios <list>` or `--role <name>`. While not critical in MVP (since a user can always run molecule directly for one scenario), this can improve usability for large projects.
* **Enhanced Reporting:** Future versions might support more report formats, such as JUnit XML (common in CI for test results) or HTML reports. JUnit XML in particular would allow integration with CI test reports visualization (and note: Molecule itself recently added JUnit output capability, which we could tap into or replicate). An HTML report could provide a one-page overview with styling (nice for posting on an intranet). These are nice-to-haves for later.
* **Detailed Failure Logs in Reports:** In MVP, the JSON/MD reports likely only have pass/fail status. In the future, we might include a snippet of error message or a path to a log file for each failed scenario. For example, Moltest could save each scenario’s Molecule output to a log file (especially on failure) and then reference that in the summary. That way, developers can quickly find the cause of failure without trawling through CI logs.
* **Integration with Version Control/PRs:** A possible enhancement is automatically commenting on a GitHub PR or GitLab MR with the Molecule test results (using their APIs), making it very visible to reviewers. This would likely be implemented outside Moltest (in CI job scripts), but we could facilitate it by providing the nicely formatted Markdown or an easy way to trigger such integration. Possibly a future “GitHub App” or similar could use Moltest under the hood.
* **Support for Windows (if demand arises):** If there’s interest in running Moltest on Windows (perhaps for Windows-targeted Ansible roles under WSL or similar), we might test and adjust for that. Currently, Molecule itself might not fully support Windows control node, so this is low priority.
* **Configuration File for Moltest:** If users want to customize behavior (like default paths, excluding certain scenarios, etc.), we might introduce a config (e.g., `moltest.cfg` or extend pyproject or so). MVP does not include this; defaults are fine. But as features grow, a config might be helpful.
* **Improved Incremental Testing:** Beyond just “last failed”, we could explore smarter incremental runs – e.g., only run scenarios related to recently changed roles or files (like what `tox -e molecule` sometimes does with scenarios, or how some build systems skip unchanged components). This would require mapping roles to tests and checking git diffs, which is complex and probably out of scope. But it’s a potential idea for large projects to save time (this might tie into CI optimization as well).

We will prioritize backlog items based on user feedback after MVP release. The plugin system is noted as desired but explicitly out-of-scope for the first version.

## Implementation Plan and Details for Prototyping

To achieve the MVP, here is an outline of the implementation approach, with actionable steps:

1. **Project Setup:** Initialize a Python project for Moltest. Define dependencies: at minimum `ansible-core>=2.15` (or ansible-base if needed) and `molecule>=X.Y` that supports it. Also include any libraries for CLI parsing and color (e.g. Click and rich, or just use argparse and simple color codes). Set up a basic console entry point (using `setuptools.entry_points` for `moltest = moltest.cli:main`).

2. **Scenario Discovery Implementation:** Write a function to walk the filesystem from current directory to find scenarios. Prototype: use `pathlib` to find all files named `molecule.yml`. Filter those that reside under a `molecule/` directory structure. For each found, derive scenario name and base path:

   * Scenario name can be obtained by looking at the parent folder name of molecule.yml (the parent might be scenario name, with parent of that being “molecule”). E.g. `/path/to/role1/molecule/default/molecule.yml` -> scenario name “default”, role name “role1”. We can capture both.
   * Base path in this case is `/path/to/role1`. We might store tuple (role1, default, base\_path). For a scenario at repo root like `/path/to/proj/molecule/aws/molecule.yml`, scenario name “aws”, role maybe None or general, base path `/path/to/proj`.
   * Ensure to avoid duplicates and ensure ordering (maybe sort scenarios by name or path to have a consistent order each run).

3. **Command Execution Loop:** For each scenario identified, run it:

   * Change working directory (using `os.chdir`) to the base path (so that running molecule uses the right context where the role is present). Alternatively, we can run `molecule` with `-c` or certain flags, but simplest is cwd.
   * Construct the command: `molecule test -s <scenario>`. If the scenario is the default named “default”, `-s default` may not be strictly required (molecule by default runs “default” if none specified). But to be explicit, we can include it.
   * Use `subprocess.run([...], capture_output=False, shell=False)` to execute, so it streams output directly to console. We might prepend a line "Running scenario X..." before calling, for user feedback. Then let molecule output flow. On completion, check `result.returncode`.
   * Capture the return code and note it (pass if 0, fail if >0). Possibly capture execution time via `time.time()` before and after to record how long it took (optional, but could include in summary).
   * After each scenario, print a one-line result (e.g., using a colored ✓ or ✗ as discussed). If we do this *after* molecule’s output, ensure to flush output properly so it doesn’t intermix badly.

4. **Result Storage:** Accumulate results in a list or dict. Key might be something like `"role1:default"` or `"role1/default"` or even the path of molecule.yml as key. Store status. Also store maybe a short message or the return code.

5. **Persistence (Cache) Handling:** Before running tests, if `--rerun-failed` is specified, load the cache file:

   * If file exists, read JSON. Extract list of failed scenarios. Filter the discovered scenario list to those that match. If none match (or file says none failed), print “No failed scenarios to rerun” and exit gracefully (0 exit, because last run had no failures).
   * If file doesn’t exist, either treat as no prior info (so if `--rerun-failed` was invoked, we could either run everything or exit with a message). It might be more intuitive to just run all (user may expect that as a fallback). However, doing a full run when they explicitly asked for rerun-failed might be surprising. Another approach: treat it as nothing to do and exit 0 with a warning. This detail can be decided; perhaps safer: run all if cache missing, so they don’t mistakenly skip testing. But also log “(no cache found, running all scenarios)”.
   * After running tests (whether full or partial), write the cache file. (We will update all scenario statuses, not just failures, so that next time we know which passed too.) Use atomic write: e.g., write to a temp file and then rename, to avoid corruption if program is interrupted mid-write.

6. **Generating Reports:** After tests complete, use the collected results to produce outputs:

   * **Console Summary:** Iterate over results and print in a formatted manner. Use color codes (e.g., `\x1b[32m` for green, `\x1b[31m` for red, resetting with `\x1b[0m`). If using an external lib like `rich`, we can print with style easily. But implementing manually is fine. Ensure alignment or clear format (maybe fixed width for scenario names or use a tab). Keep each entry to one line for readability. Then print total line.
   * **JSON file:** If `--json-report` was provided, open that file and dump a JSON structure. For structure, a list of objects or a dict is fine. Perhaps:

     ```json
     {
       "total_scenarios": 7,
       "scenarios": [
         {"id": "role1:default", "name": "default", "role": "role1", "status": "passed", "duration": 120.5},
         {"id": "role1:upgrade", "name": "upgrade", "role": "role1", "status": "failed", "duration": 130.2, "return_code": 1},
         ...
       ],
       "passed": 6,
       "failed": 1,
       "timestamp": "2025-07-01T15:30:00Z"
     }
     ```

     (We include counts and timestamp for completeness.)
   * **Markdown file:** If `--md-report` given, create a Markdown formatted text. Possibly as a table (as shown above) or list. Tables are more structured but lists might be easier to read in plain text form. Either is acceptable; we can choose table for a cleaner column alignment in the Markdown preview. Ensure to write the file with UTF-8 encoding (if using emojis like checkmarks). If emojis cause any issues, we can stick to text "Pass/Fail". But emojis in Markdown can be nice (✅, ❌).
   * After writing files, if in an interactive context (not CI), we could print a note like “Report saved to results.md” to confirm to user. In CI, that message would just appear in logs which is fine.

7. **Testing & Validation:** As we prototype, test the tool on a sample repository with multiple Molecule scenarios:

   * Create a dummy set of roles with trivial molecule tests to verify discovery works.
   * Simulate various scenarios: all pass, some fail (perhaps introduce a known failure), then test `--rerun-failed`.
   * Test that the summary shows correct info and that the exit code is correct.
   * Test on macOS and Linux (perhaps via a container run) to ensure no path issues.
   * Test integration with a CI-like environment: e.g., run in a Docker container that has only CLI (no color by default) and see if `--no-color` works.
   * Check that using Ansible 2.15 and a supported Molecule version yields no compatibility error. If Molecule/Ansible version mismatches cause warnings, note them. (E.g., Molecule might warn if Ansible is too new but it should support 2.15 if we have the right version).
   * If possible, test the tool with a slightly newer Ansible (like 2.16 beta if available) to see forward compatibility.

8. **Documentation for Users:** Though not code, part of implementation is writing documentation (perhaps in the README). This should cover installation (pip install command), basic usage examples, description of options, and an example in CI. Also mention the recommended Ansible/Molecule versions and any limitations (like “only Docker driver tested if parallel is used”, etc.).

By following these steps, an initial prototype of Moltest can be developed and refined. Early prototyping should focus on the core flow (discovery -> run -> summary) to prove that it works end-to-end. Once that is working, adding the reporting output and cache persistence are relatively straightforward enhancements to layer on. We should also gather feedback from a couple of users (or team members) who can try Moltest on their Molecule test sets, to see if the output is understandable and if the tool indeed saves them effort. This feedback can guide any tweaks to the output format or behavior before declaring the MVP ready.

With this approach, Moltest will deliver a much-needed improvement to the Ansible testing workflow, making it easier to run comprehensive test suites and quickly identify any issues, all while integrating smoothly into modern development pipelines.
