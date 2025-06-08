# Contributor Guide for Moltest

This guide is for AI agents and human contributors working on the `moltest` project.

## Project Overview

*   **Main Application Code:** Resides in the `moltest/` directory.
    *   The primary CLI logic is in `moltest/cli.py`.
    *   Core functionalities like scenario discovery, caching, and reporting are in their respective modules within `moltest/`.
*   **Tests:** All tests are located in the `tests/` directory. We use `pytest`.
*   **Configuration:** Project configuration is managed in `pyproject.toml`.

## Dev Environment Tips

*   **Python Version Management:** This project uses a specific Python version defined in `.python-version`, managed by `pyenv`.
*   **Virtual Environments & Dependencies:** It's recommended to use `uv` for creating virtual environments and managing dependencies.
    *   To install dependencies: `uv pip install -r requirements.txt` (if one exists) or `uv pip install .` for project dependencies, and `uv pip install .[test]` for test dependencies.
*   **Running Moltest Locally:** After installation in your virtual environment, you should be able to run `moltest --help`.

## Testing Instructions

*   **Running All Tests:**
    *   From the project root, run `pytest`. This will discover and execute all tests in the `tests/` directory.
*   **Focusing on Specific Tests:**
    *   To run a specific test file: `pytest tests/test_cli_run.py`
    *   To run a specific test function: `pytest tests/test_cli_run.py -k test_run_streams_output_verbose`
*   **Test Coverage:** Aim for good test coverage for any new features or bug fixes.
*   **Validation:**
    *   Ensure all tests pass before committing changes: `pytest`.
    *   If linters (e.g., Flake8, Black, Ruff) are configured, run them to ensure code style consistency. (Agent: Please check `pyproject.toml` or for linter config files if unsure).
*   **Adding Tests:**
    *   New functionality should be accompanied by new tests.
    *   Bug fixes should ideally include a test that reproduces the bug and verifies the fix.

## Contribution and Style Guidelines

*   **Code Style:** Follow PEP 8 guidelines for Python code. Use linters and formatters if available in the project setup.
*   **Docstrings:** Add clear docstrings to new functions, classes, and modules.
*   **Commit Messages:** Write clear and concise commit messages.
*   **Breaking Down Tasks:** For complex changes, break them down into smaller, logical, and testable steps.

## How Agents Should Work

*   **Understand the Goal:** Before making changes, ensure you understand the task requirements. Ask for clarification if needed.
*   **Locate Relevant Code:** Use tools to find the specific files and functions related to the task. Start with `moltest/cli.py` for CLI-related tasks.
*   **Implement Incrementally:** Make changes in small, verifiable steps.
*   **Test Your Changes:** Utilize the `pytest` framework to run existing tests and add new ones for your changes.
*   **Provide Context:** When presenting your work or asking for reviews, provide context about the changes made and how they address the task.
*   **Documentation:** If changes affect user-facing behavior or internal APIs, update relevant documentation (e.g., README, docstrings).

## PR (Pull Request) Instructions

*   **Title Format:** `feat: <Brief description of feature>` or `fix: <Brief description of fix>` or `test: <Description of test changes>`.
*   **Description:** Clearly describe the changes made, the problem solved, and how to test the changes.
*   **Link to Issues:** If the PR addresses a specific issue, link to it.
