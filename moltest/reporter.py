#!/usr/bin/env python3
# reporter.py - Handles console output formatting and colorization.

import colorama
from colorama import Fore, Back, Style
import json
from datetime import datetime, timezone

# Initialize colorama
# autoreset=True ensures that color/style changes are reset after each print.
colorama.init(autoreset=True)

# Define color constants for different message types
COLOR_SUCCESS = Fore.GREEN
COLOR_FAILURE = Fore.RED
COLOR_WARNING = Fore.YELLOW
COLOR_INFO = Fore.BLUE
COLOR_HEADER = Fore.CYAN
COLOR_DEBUG = Fore.MAGENTA
COLOR_MUTED = Fore.LIGHTBLACK_EX # Or Style.DIM + Fore.WHITE for some terminals

# Define style constants
STYLE_BOLD = Style.BRIGHT
STYLE_DIM = Style.DIM
STYLE_NORMAL = Style.NORMAL

def print_scenario_start(scenario_id: str, verbose: int = 0):
    """Prints a message indicating the start of a scenario."""
    # Basic implementation for now, verbose not used yet
    print(f"{COLOR_INFO}RUNNING: {scenario_id} ...")

def print_scenario_result(scenario_id: str, status: str, duration: float = None, verbose: int = 0):
    """Prints the result of a scenario execution with color coding."""
    status_upper = status.upper()
    
    if status_upper == "PASSED":
        color = COLOR_SUCCESS
        status_text = "PASSED"
    elif status_upper == "FAILED":
        color = COLOR_FAILURE
        status_text = "FAILED"
    else:
        color = COLOR_WARNING
        status_text = status_upper # Or some other default
        
    duration_str = f" ({duration:.2f}s)" if duration is not None else ""
    
    # Basic implementation for now, verbose not used yet
    print(f"{color}{STYLE_BOLD}{status_text}:{STYLE_NORMAL} {scenario_id}{duration_str}")


def print_summary_table(scenario_results: list, overall_duration: float = None, verbose: int = 0):
    """Prints a summary table of all scenario results."""
    if not scenario_results:
        print(f"{COLOR_WARNING}No scenario results to summarize.")
        return

    num_total = len(scenario_results)
    num_passed = sum(1 for r in scenario_results if r.get('status', '').lower() == 'passed')
    num_failed = sum(1 for r in scenario_results if r.get('status', '').lower() == 'failed')
    num_other = num_total - num_passed - num_failed

    # Determine column widths for alignment
    # Max length of scenario ID, or default to 'Scenario ID'
    max_id_len = max(len(r.get('id', '')) for r in scenario_results) 
    max_id_len = max(max_id_len, len("Scenario ID"))
    status_col_len = len("  Status  ") # Length of "  PASSED  " or "  FAILED  "
    duration_col_len = len("(000.00s)") # Max duration string length

    print(f"\n{COLOR_HEADER}{STYLE_BOLD}{'=' * 20} Test Execution Summary {'=' * 20}{STYLE_NORMAL}")
    
    # Header row
    header = f"{STYLE_BOLD}{'Scenario ID':<{max_id_len}}  {'Status':^{status_col_len}}  {'Duration':>{duration_col_len}}{STYLE_NORMAL}"
    print(header)
    print(f"{'-' * (max_id_len + status_col_len + duration_col_len + 4)}") # Separator line

    for result in scenario_results:
        s_id = result.get('id', 'N/A')
        s_status = result.get('status', 'UNKNOWN').upper()
        s_duration = result.get('duration')

        if s_status == "PASSED":
            color = COLOR_SUCCESS
            status_display = "PASSED"
        elif s_status == "FAILED":
            color = COLOR_FAILURE
            status_display = "FAILED"
        else:
            color = COLOR_WARNING
            status_display = s_status
        
        duration_display = f"({s_duration:.2f}s)" if s_duration is not None else ""
        
        print(f"{s_id:<{max_id_len}}  {color}{STYLE_BOLD}{status_display:^{status_col_len}}{STYLE_NORMAL}  {duration_display:>{duration_col_len}}")

    print(f"{'-' * (max_id_len + status_col_len + duration_col_len + 4)}") # Separator line

    # Summary counts
    summary_line = f"{STYLE_BOLD}Total Scenarios: {num_total}{STYLE_NORMAL} | " \
                   f"{COLOR_SUCCESS}{STYLE_BOLD}Passed: {num_passed}{STYLE_NORMAL} | " \
                   f"{COLOR_FAILURE}{STYLE_BOLD}Failed: {num_failed}{STYLE_NORMAL}"
    if num_other > 0:
        summary_line += f" | {COLOR_WARNING}{STYLE_BOLD}Other: {num_other}{STYLE_NORMAL}"
    print(summary_line)

    if overall_duration is not None:
        print(f"{STYLE_BOLD}Total Execution Time: {overall_duration:.2f}s{STYLE_NORMAL}")
    print(f"{COLOR_HEADER}{STYLE_BOLD}{'=' * (len(header) + 0)}{STYLE_NORMAL}") # Match header length


def generate_json_report(scenario_results: list, report_path: str, overall_duration: float = None, verbose: int = 0):
    """Generates a JSON report of test execution results."""
    if not scenario_results:
        if verbose > 0:
            print(f"{COLOR_WARNING}No scenario results to generate JSON report.")
        # Create an empty/default report if no results
        report_data = {
            'total_scenarios': 0,
            'scenarios': [],
            'passed': 0,
            'failed': 0,
            'other': 0,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_duration': overall_duration
        }
    else:
        num_total = len(scenario_results)
        num_passed = sum(1 for r in scenario_results if r.get('status', '').lower() == 'passed')
        num_failed = sum(1 for r in scenario_results if r.get('status', '').lower() == 'failed')
        num_other = num_total - num_passed - num_failed

        processed_scenarios = []
        for r in scenario_results:
            scenario_id = r.get('id', 'unknown:unknown')
            role_name, scenario_name = scenario_id.split(':', 1) if ':' in scenario_id else ('unknown', scenario_id)
            
            processed_scenarios.append({
                'id': scenario_id,
                'name': scenario_name,
                'role': role_name,
                'status': r.get('status', 'UNKNOWN').lower(),
                'duration': r.get('duration'),
                'return_code': r.get('return_code', -1) # Assuming -1 if not present
            })

        report_data = {
            'total_scenarios': num_total,
            'scenarios': processed_scenarios,
            'passed': num_passed,
            'failed': num_failed,
            'other': num_other,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_duration': overall_duration
        }

    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=4)
        if verbose > 0:
            print(f"{COLOR_SUCCESS}JSON report generated successfully at {report_path}")
    except IOError as e:
        print(f"{COLOR_FAILURE}Error writing JSON report to {report_path}: {e}")


def generate_markdown_report(scenario_results: list, report_path: str, overall_duration: float = None, verbose: int = 0):
    """Generates a Markdown report of test execution results."""
    lines = []
    timestamp_str = datetime.now(timezone.utc).isoformat()

    lines.append("# Molecule Test Execution Report")
    lines.append(f"**Generated:** {timestamp_str}\n")

    if not scenario_results:
        lines.append("No scenario results to report.")
        if verbose > 0:
            print(f"{COLOR_WARNING}No scenario results to generate Markdown report.")
    else:
        num_total = len(scenario_results)
        num_passed = sum(1 for r in scenario_results if r.get('status', '').lower() == 'passed')
        num_failed = sum(1 for r in scenario_results if r.get('status', '').lower() == 'failed')
        num_other = num_total - num_passed - num_failed

        lines.append("## Summary")
        lines.append(f"- **Total Scenarios:** {num_total}")
        lines.append(f"- **Passed:** {num_passed} ✅")
        lines.append(f"- **Failed:** {num_failed} ❌")
        if num_other > 0:
            lines.append(f"- **Other/Skipped:** {num_other} ⚠️")
        if overall_duration is not None:
            lines.append(f"- **Total Execution Time:** {overall_duration:.2f}s")
        lines.append("") # Newline

        lines.append("## Scenario Details")
        lines.append("| Scenario ID | Status | Duration (s) |")
        lines.append("|---|---|---|")

        for r in scenario_results:
            scenario_id = r.get('id', 'N/A')
            status = r.get('status', 'UNKNOWN').lower()
            duration = r.get('duration')
            duration_str = f"{duration:.2f}" if duration is not None else "N/A"
            
            status_emoji = ""
            if status == "passed":
                status_emoji = "✅ Passed"
            elif status == "failed":
                status_emoji = "❌ Failed"
            else:
                status_emoji = f"⚠️ {status.capitalize()}"
            
            lines.append(f"| {scenario_id} | {status_emoji} | {duration_str} |")

    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        if verbose > 0:
            print(f"{COLOR_SUCCESS}Markdown report generated successfully at {report_path}")
    except IOError as e:
        print(f"{COLOR_FAILURE}Error writing Markdown report to {report_path}: {e}")

if __name__ == '__main__':
    # Example usage (will be removed or moved to tests later)
    print(f"{COLOR_HEADER}{STYLE_BOLD}Reporter Module Initialized{STYLE_NORMAL}")
    print(f"{COLOR_SUCCESS}This is a success message.")
    print(f"{COLOR_FAILURE}This is a failure message.")
    print(f"{COLOR_WARNING}This is a warning message.")
    print(f"{COLOR_INFO}This is an info message.")
    print(f"{COLOR_DEBUG}This is a debug message.")
    print(f"{COLOR_MUTED}This is a muted/dim message.")
    print(f"A {STYLE_BOLD}bold{STYLE_NORMAL} and {STYLE_DIM}dim{STYLE_NORMAL} message.")
    print("Autoreset should make this default color.")

    print(f"\n{COLOR_HEADER}--- Scenario Reporting Examples ---{STYLE_NORMAL}")
    print_scenario_start("scenario_01_fast_pass")
    print_scenario_result("scenario_01_fast_pass", "passed", duration=0.52)

    print_scenario_start("scenario_02_slow_fail")
    print_scenario_result("scenario_02_slow_fail", "failed", duration=10.7)
    
    print_scenario_start("scenario_03_no_duration")
    print_scenario_result("scenario_03_no_duration", "passed")

    print_scenario_start("scenario_04_custom_status")
    print_scenario_result("scenario_04_custom_status", "skipped")

    print(f"\n{COLOR_HEADER}--- Summary Table Example ---{STYLE_NORMAL}")
    example_results = [
        {'id': 'scenario_01_alpha', 'status': 'passed', 'duration': 1.23},
        {'id': 'scenario_02_beta_very_long_name', 'status': 'failed', 'duration': 10.7},
        {'id': 'scenario_03_gamma', 'status': 'passed', 'duration': 0.88},
        {'id': 'scenario_04_delta', 'status': 'skipped'},
        {'id': 'scenario_05_epsilon', 'status': 'passed', 'duration': 2.4567},
    ]
    print_summary_table(example_results, overall_duration=15.2667)

    print(f"\n{COLOR_HEADER}--- Empty Summary Table Example ---{STYLE_NORMAL}")
    print_summary_table([])

    print(f"\n{COLOR_HEADER}--- JSON Report Example ---{STYLE_NORMAL}")
    # Assume 'return_code' is now part of example_results for full demonstration
    example_results_for_json = [
        {'id': 'myrole:scenario_01_alpha', 'status': 'passed', 'duration': 1.23, 'return_code': 0},
        {'id': 'myrole:scenario_02_beta_very_long_name', 'status': 'failed', 'duration': 10.7, 'return_code': 1},
        {'id': 'anotherrole:scenario_03_gamma', 'status': 'passed', 'duration': 0.88, 'return_code': 0},
        {'id': 'myrole:scenario_04_delta', 'status': 'skipped', 'return_code': 0}, # duration might be None
        {'id': 'anotherrole:scenario_05_epsilon', 'status': 'passed', 'duration': 2.4567, 'return_code': 0},
    ]
    json_report_path = "./test_report.json"
    generate_json_report(example_results_for_json, json_report_path, overall_duration=15.2667, verbose=1)
    print(f"{COLOR_INFO}Check {json_report_path} for the JSON output.")

    print(f"\n{COLOR_HEADER}--- Empty JSON Report Example ---{STYLE_NORMAL}")
    empty_json_report_path = "./empty_test_report.json"
    generate_json_report([], empty_json_report_path, overall_duration=0.0, verbose=1)
    print(f"{COLOR_INFO}Check {empty_json_report_path} for the empty JSON output.")

    print(f"\n{COLOR_HEADER}--- Markdown Report Example ---{STYLE_NORMAL}")
    md_report_path = "./test_report.md"
    generate_markdown_report(example_results_for_json, md_report_path, overall_duration=15.2667, verbose=1)
    print(f"{COLOR_INFO}Check {md_report_path} for the Markdown output.")

    print(f"\n{COLOR_HEADER}--- Empty Markdown Report Example ---{STYLE_NORMAL}")
    empty_md_report_path = "./empty_test_report.md"
    generate_markdown_report([], empty_md_report_path, overall_duration=0.0, verbose=1)
    print(f"{COLOR_INFO}Check {empty_md_report_path} for the empty Markdown output.")
