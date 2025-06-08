# Reporter Module Examples

The `moltest.reporter` module provides helper functions for colorized output and report generation. Below are simple examples demonstrating the available APIs.

```python
from moltest import reporter

# Display progress and result for a scenario
reporter.print_scenario_start("scenario_01")
reporter.print_scenario_result("scenario_01", "passed", duration=0.52)

# Summaries can be printed and saved in JSON or Markdown formats
example_results = [
    {"id": "role1:alpha", "status": "passed", "duration": 1.23},
    {"id": "role2:beta", "status": "failed", "duration": 10.7},
    {"id": "role3:gamma", "status": "skipped"},
]
reporter.print_summary_table(example_results, overall_duration=12.45)
reporter.generate_json_report(example_results, "report.json", overall_duration=12.45)
reporter.generate_markdown_report(example_results, "report.md", overall_duration=12.45)
```

These examples were previously embedded in `moltest/reporter.py` under a `__main__` guard. They have been moved here for reference.
