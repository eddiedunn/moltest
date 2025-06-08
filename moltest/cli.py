#!/usr/bin/env python3
import click
import subprocess
import re
import os
import sys
import time
from pathlib import Path
from importlib import import_module
from importlib.metadata import entry_points
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import __version__

# Regex to match ANSI escape sequences for cleaning command output
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE_RE.sub("", text)

from .discovery import discover_scenarios
from .cache import (
    load_cache,
    save_cache,
    update_scenario_status,
    get_failed_scenarios,
    CACHE_FILENAME,
    get_empty_cache_structure,
)
from .config import load_config, save_config
from .reporter import (
    print_scenario_start,
    print_scenario_result,
    print_summary_table,
    generate_json_report,
    generate_markdown_report,
    generate_junit_xml_report,
)

# _PROJECT_ROOT is the current working directory from which moltest is invoked.
# This is where the .moltest_cache.json will be expected/created.
_PROJECT_ROOT = Path.cwd()

# Default paths used by the CLI
DEFAULT_JSON_REPORT = "moltest_report.json"
DEFAULT_MD_REPORT = "moltest_report.md"
DEFAULT_JUNIT_REPORT = "moltest_report.xml"
DEFAULT_ROLES_PATH = "roles"

# --- Plugin and Hook System -------------------------------------------------

_loaded_plugins: list = []


def load_plugins() -> list:
    """Load plugin modules via entry points and configuration."""
    plugins = []
    config = load_config()
    plugin_names = config.get("plugins", []) if isinstance(config, dict) else []

    try:
        for ep in entry_points(group="moltest.plugins"):
            try:
                plugins.append(ep.load())
            except Exception as exc:  # pragma: no cover - rare import failure
                click.echo(
                    click.style(
                        f"Failed to load entry point plugin {ep.name}: {exc}",
                        fg="yellow",
                    )
                )
    except Exception:  # pragma: no cover - no entry points found
        pass

    for name in plugin_names:
        try:
            plugins.append(import_module(name))
        except Exception as exc:  # pragma: no cover - invalid plugin
            click.echo(
                click.style(f"Failed to load plugin {name}: {exc}", fg="yellow")
            )

    return plugins


def call_hooks(hook: str, *args, **kwargs) -> None:
    """Invoke a hook on all loaded plugins."""
    for mod in _loaded_plugins:
        func = getattr(mod, hook, None)
        if callable(func):
            try:
                func(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - plugin error
                click.echo(
                    click.style(f"Plugin hook {hook} failed: {exc}", fg="yellow")
                )

# Attempt to import packaging.version for robust version comparison
try:
    from packaging.version import parse as parse_version, InvalidVersion
except ImportError:
    parse_version = None
    InvalidVersion = None
    click.echo(click.style("Warning: 'packaging' library not found. Version comparison might be less robust. Consider 'pip install packaging'.", fg='yellow'), err=True)

def check_dependencies(ctx):
    """Checks for presence of molecule and ansible commands."""
    min_versions = {
        "ansible": "2.15.0",
        "molecule": "4.0.0"
    }
    dependencies = {
        "molecule": {
            "cmd": ["molecule", "--version"],
            "version_regex": r"molecule\s+([0-9]+(?:\.[0-9]+)+)"
        },
        "ansible": {
            "cmd": ["ansible", "--version"],
            "version_regex": r"ansible \[core ([\d\.]+)\]"
        }
    }
    issues = []

    for dep_name, dep_info in dependencies.items():
        cmd_args = dep_info["cmd"]
        version_str = None
        try:
            process = subprocess.run(cmd_args, capture_output=True, text=True, check=False)
            if process.returncode == 0:
                output = strip_ansi(process.stdout.strip())
                match = re.search(dep_info["version_regex"], output)
                if match and match.group(1):
                    version_str = match.group(1)
                    if parse_version:
                        try:
                            current_v = parse_version(version_str)
                            required_v = parse_version(min_versions[dep_name])
                            if current_v < required_v:
                                issues.append(f"{dep_name.capitalize()} version {version_str} is below required {min_versions[dep_name]}.")
                        except InvalidVersion:
                            issues.append(f"Could not parse {dep_name.capitalize()} version: {version_str}")
                    else: # Fallback to basic string comparison if packaging.version is not available
                        if version_str < min_versions[dep_name]: # This is a simplification
                             issues.append(f"{dep_name.capitalize()} version {version_str} may be below required {min_versions[dep_name]} (basic check).")
                else:
                    issues.append(f"Could not extract {dep_name.capitalize()} version from output: {output[:100]}...")
            else:
                issues.append(f"Command '{' '.join(cmd_args)}' failed with code {process.returncode}. Stderr: {process.stderr.strip()[:100]}...")
        except FileNotFoundError:
            issues.append(f"{dep_name.capitalize()} command not found.")
        except Exception as e:
            issues.append(f"Error checking {dep_name.capitalize()}: {e}")

    if issues:
        error_message = "Dependency and version check failed:\n" + "\n".join([f"  - {issue}" for issue in issues])
        error_message += "\nPlease ensure Ansible Core >= 2.15 and Molecule >= 4.0 are installed and in your PATH."
        click.echo(click.style(error_message, fg="red"), err=True)
        ctx.exit(4) # Exit code for dependency/version errors


def get_version_message():
    script_version = __version__
    # Temporarily disabled to bypass environment issues for testing
    ansible_version = "X.Y.Z (ansible version check disabled)"
    molecule_version = "A.B.C (molecule version check disabled)"
    return f"%(prog)s, version %(version)s\n{ansible_version}\n{molecule_version}"

@click.group()
@click.version_option(version=__version__, prog_name='moltest', message=get_version_message())
def cli():
    """A CLI tool for running Molecule tests and generating reports."""
    pass

def validate_report_path(ctx, param, value, expected_extension):
    if value is None:
        return None
    
    report_path = Path(value)
    
    if report_path.suffix.lower() != expected_extension.lower():
        raise click.BadParameter(
            f"Report file '{value}' must have a '{expected_extension}' extension.",
            ctx=ctx,
            param=param
        )
    
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise click.BadParameter(
            f"Could not create parent directory for '{value}': {e}",
            ctx=ctx,
            param=param
        )
        
    return str(report_path)  # Return as string, Click Path type will handle further checks


def compile_id_expression(expression: str):
    """Compile an ID matching expression similar to pytest's ``-k`` option."""

    if not expression:
        return lambda _id: True

    token_re = re.compile(r"\(|\)|\band\b|\bor\b|\bnot\b|[^()\s]+")
    tokens = token_re.findall(expression)
    parts: list[str] = []
    for tok in tokens:
        if tok in {"and", "or", "not", "(", ")"}:
            parts.append(tok)
        else:
            parts.append(f"({tok!r} in scenario_id)")
    python_expr = " ".join(parts)

    def matcher(scenario_id: str) -> bool:
        try:
            return bool(eval(python_expr, {"__builtins__": {}}, {"scenario_id": scenario_id}))
        except Exception:
            return False

    return matcher


def _run_scenario(record, verbose, roles_path_resolved):
    """Execute a single Molecule scenario and capture its output."""
    full_id = record['id']
    scenario_name = record['scenario_name']
    execution_path = record['execution_path']
    param_vars = record.get('vars', {})
    is_xfail = record.get('is_xfail', False)

    molecule_command = f"molecule test -s {scenario_name}"
    output_lines = []
    scenario_status = "unknown"
    duration = None
    return_code = -1
    error_message = None
    try:
        if verbose > 0:
            output_lines.append(f"    Running command: {molecule_command}")
        command_parts = molecule_command.split()
        start_time = time.monotonic()
        env = os.environ.copy()
        env['ANSIBLE_ROLES_PATH'] = str(roles_path_resolved)
        for k, v in param_vars.items():
            env[str(k)] = str(v)
        with subprocess.Popen(
            command_parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=execution_path,
            env=env,
        ) as proc:
            if verbose > 0:
                for line in proc.stdout:
                    output_lines.append(f"      {line.strip()}")
            else:
                proc.wait()
        end_time = time.monotonic()
        duration = end_time - start_time
        return_code = proc.returncode
        scenario_status = "passed" if return_code == 0 else "failed"
        if is_xfail:
            if scenario_status == "failed":
                scenario_status = "xfailed"
                return_code = 0
            else:
                scenario_status = "xpassed"
    except FileNotFoundError:
        error_message = (
            "    Error: molecule command not found. Is Molecule installed and in PATH?"
        )
        scenario_status = "failed"
    except Exception as e:  # pragma: no cover - unexpected errors
        scenario_status = "failed"
        if verbose > 0:
            output_lines.append(
                click.style(f"    ERROR during {full_id}: {e}", fg='red')
            )

    return {
        'id': full_id,
        'status': scenario_status,
        'duration': duration,
        'return_code': return_code,
        'output_lines': output_lines,
        'error_message': error_message,
    }

@cli.command()
@click.pass_context # Add pass_context decorator
@click.option(
    '--rerun-failed',
    '--lf',
    '-f',
    'rerun_failed',
    is_flag=True,
    help='Rerun only the failed tests.'
)
@click.option('--json-report', '-j',
              type=click.Path(dir_okay=False, writable=True, resolve_path=True),
              flag_value=DEFAULT_JSON_REPORT,
              default=None,
              callback=lambda ctx, param, value: validate_report_path(ctx, param, value, '.json'),
              help=f'Output test results as a JSON file. Defaults to {DEFAULT_JSON_REPORT}.')
@click.option('--md-report', '-m',
              type=click.Path(dir_okay=False, writable=True, resolve_path=True),
              flag_value=DEFAULT_MD_REPORT,
              default=None,
              callback=lambda ctx, param, value: validate_report_path(ctx, param, value, '.md'),
              help=f'Output test results as a Markdown file. Defaults to {DEFAULT_MD_REPORT}.')
@click.option('--junit-xml', '-x',
              type=click.Path(dir_okay=False, writable=True, resolve_path=True),
              flag_value=DEFAULT_JUNIT_REPORT,
              default=None,
              callback=lambda ctx, param, value: validate_report_path(ctx, param, value, '.xml'),
              help=f'Output test results as a JUnit XML file. Defaults to {DEFAULT_JUNIT_REPORT}.')
@click.option('--no-color', is_flag=True, help='Disable colored output.')
@click.option('--verbose', '-v', count=True, help='Enable verbose output. Use -vv or -vvv for more verbosity.')
@click.option('--scenario', '-s', default='all', help='Specify scenario(s) to run: "all", a specific ID, or comma-separated IDs.')
@click.option('-k', 'id_expr', default=None, help='Filter scenarios by ID expression (e.g., "foo and not bar")')
@click.option('--skip', 'skip_tags', multiple=True, help='Skip scenarios matching the given tag. Can be used multiple times.')
@click.option('--xfail', 'xfail_tags', multiple=True, help='Expect failure for scenarios with the given tag. Can be used multiple times.')
@click.option('--parallel', '-p', default=1, type=int, show_default=True,
              help='Number of scenarios to run concurrently.')
@click.option(
    '--fail-fast',
    is_flag=True,
    help='Stop execution after the first failure.'
)
@click.option(
    '--maxfail',
    default=0,
    type=int,
    show_default=True,
    help='Abort after this many failures. 0 means unlimited.'
)
@click.option(
    '--roles-path',
    '-r',
    type=click.Path(file_okay=False, resolve_path=True),
    default=None,
    help='Directory containing Ansible roles. Used for ANSIBLE_ROLES_PATH.',
)
def run(ctx, rerun_failed, json_report, md_report, junit_xml, no_color, verbose, scenario,
        id_expr, skip_tags, xfail_tags, parallel, fail_fast, maxfail, roles_path):  # Add ctx parameter
    """Run Molecule tests."""
    check_dependencies(ctx)  # Call dependency check early

    if os.getenv('CI', '').lower() == 'true' or not sys.stdout.isatty():
        no_color = True

    color_enabled = not no_color

    global _loaded_plugins
    _loaded_plugins = load_plugins()
    call_hooks("before_run", ctx)

    config = load_config()
    if roles_path is None:
        roles_path = config.get('roles_path')
        if roles_path is None:
            if sys.stdin.isatty():
                roles_path = click.prompt('Path to Ansible roles', default=DEFAULT_ROLES_PATH)
                save_config({'roles_path': roles_path})
            else:
                roles_path = DEFAULT_ROLES_PATH
    else:
        if roles_path != config.get('roles_path'):
            save_config({'roles_path': roles_path})

    if verbose > 0:
        click.echo(f"Rerun failed: {rerun_failed}")
        click.echo(f"JSON report: {json_report}")
        click.echo(f"Markdown report: {md_report}")
        click.echo(f"JUnit XML: {junit_xml}")
        click.echo(f"No color: {no_color}")
        click.echo(f"  Verbose: {verbose}")
        click.echo(f"  Parallel: {parallel}")
        click.echo(f"  Fail fast: {fail_fast}")
        click.echo(f"  Max fail: {maxfail}")
        click.echo(f"  Scenario(s) selected: {scenario}")
        click.echo(f"  Skip tags: {', '.join(skip_tags) if skip_tags else 'None'}")
        click.echo(f"  XFail tags: {', '.join(xfail_tags) if xfail_tags else 'None'}")
        click.echo(f"  Roles path: {roles_path}")

    roles_path_resolved = Path(roles_path)
    if not roles_path_resolved.is_absolute():
        roles_path_resolved = (_PROJECT_ROOT / roles_path_resolved).resolve()
    skip_tags_set = set(skip_tags)
    xfail_tags_set = set(xfail_tags)
    if verbose > 0:
        click.echo(f"  Using roles path: {roles_path_resolved}")

        # _PROJECT_ROOT is defined at the top of the file by the cache import setup
        click.echo(f"\nProject root: {_PROJECT_ROOT}")
        click.echo(f"Discovering scenarios from: {_PROJECT_ROOT}")

    try:
        cache_data = load_cache(str(_PROJECT_ROOT))
    except (IOError, OSError) as e:
        click.echo(click.style(f"Error loading cache file: {e}", fg="red"), err=True)
        ctx.exit(5) # Exit code for cache read error
    all_discovered_scenarios = []
    scenario_results_list = []
    overall_start_time = time.monotonic()
    
    try:
        all_discovered_scenarios = discover_scenarios(_PROJECT_ROOT)
        if all_discovered_scenarios:
            click.echo("Discovered scenario IDs:")
            for s_data_item in all_discovered_scenarios:
                click.echo(f"  - {s_data_item['id']}")
        else:
            click.echo(click.style("Error: No Molecule scenarios discovered in the project.", fg="red"), err=True)
            ctx.exit(2)
        
        # Determine initial target_scenarios based on 'scenario' param.
        target_scenarios = []
        if scenario.lower() == 'all':
            target_scenarios = all_discovered_scenarios
            click.echo("\nTargeting all discovered scenarios.")
        else:
            requested_ids = {s_id.strip() for s_id in scenario.split(',')}
            target_scenarios = [s for s in all_discovered_scenarios if s['id'] in requested_ids]
            
            if not target_scenarios: # User asked for specific scenarios, but none of them exist among discovered ones
                click.echo(click.style(f"Error: None of the requested scenarios ({', '.join(sorted(list(requested_ids)))}) were found among the discovered scenarios. Discovered IDs: {[s['id'] for s in all_discovered_scenarios]}", fg="red"), err=True)
                ctx.exit(2)
            else:
                click.echo("\nTargeting specific scenarios based on input:")
                for ts in target_scenarios:
                    click.echo(f"  - {ts['id']}")

        if id_expr:
            matcher = compile_id_expression(id_expr)
            target_scenarios = [s for s in target_scenarios if matcher(s['id'])]
            if verbose > 0:
                click.echo(f"\nApplying -k expression: {id_expr}")
                for ts in target_scenarios:
                    click.echo(f"  - {ts['id']}")

        # Apply --rerun-failed filter to the current target_scenarios
        scenarios_to_run = []
        if rerun_failed:
            click.echo(click.style("\n--rerun-failed specified. Filtering for previously failed scenarios.", fg='yellow'))
            failed_scenario_ids_from_cache = get_failed_scenarios(cache_data)
            
            if not failed_scenario_ids_from_cache:
                click.echo(click.style("  No failed scenarios found in cache. --rerun-failed means no tests will be run from the current selection.", fg='yellow'))
                scenarios_to_run = [] 
            else:
                click.echo(f"  Found {len(failed_scenario_ids_from_cache)} failed scenarios in cache: {', '.join(sorted(list(failed_scenario_ids_from_cache)))}")
                scenarios_to_run = [s for s in target_scenarios if s['id'] in failed_scenario_ids_from_cache]
                if not scenarios_to_run:
                    click.echo(click.style("  None of the currently targeted scenarios were found in the list of previously failed scenarios.", fg='yellow'))
        else:
            scenarios_to_run = target_scenarios # If not --rerun-failed, run all initially targeted scenarios

        # Final check: if no scenarios are selected to run, exit cleanly.
        if not scenarios_to_run:
            click.echo(click.style("\nNo Molecule tests will be run based on current filters and cache state.", fg='yellow'))
            try:
                save_cache(cache_data, str(_PROJECT_ROOT)) # Save cache to update last_run timestamp
            except (IOError, OSError) as e:
                click.echo(click.style(f"Warning: Could not save cache file after determining no tests to run: {e}", fg="yellow"), err=True)
            call_hooks("after_run", [])
            ctx.exit(0) # Exit code 0 as no tests were meant to run.

        click.echo("\nPreparing to execute Molecule tests for targeted scenarios:")
        try:
            execution_records = []
            for s_data in scenarios_to_run:
                scenario_id_base = s_data['id']
                scenario_name = s_data['scenario_name']
                execution_path = Path(s_data['execution_path'])
                param_sets = s_data.get('parameters') or [{'id': 'default', 'vars': {}}]
                tags = set(s_data.get('tags', []))

                for idx, param in enumerate(param_sets):
                    param_id = param.get('id', str(idx))
                    full_id = (
                        scenario_id_base
                        if (
                            s_data.get('parameters') is None
                            and param_id == 'default'
                            and len(param_sets) == 1
                        )
                        else f"{scenario_id_base}[{param_id}]"
                    )

                    if tags & skip_tags_set:
                        click.echo(
                            f"Skipping {full_id} due to tag match: {', '.join(tags & skip_tags_set)}"
                        )
                        print_scenario_result(
                            full_id,
                            "skipped",
                            None,
                            verbose=verbose,
                            color_enabled=color_enabled,
                        )
                        scenario_results_list.append(
                            {
                                'id': full_id,
                                'status': 'skipped',
                                'duration': None,
                                'return_code': 0,
                            }
                        )
                        update_scenario_status(cache_data, full_id, 'skipped')
                        call_hooks("after_scenario", full_id, 'skipped')
                        continue

                    execution_records.append(
                        {
                            'id': full_id,
                            'scenario_name': scenario_name,
                            'execution_path': execution_path,
                            'vars': param.get('vars', {}),
                            'is_xfail': bool(tags & xfail_tags_set),
                        }
                    )

            futures = {}
            failure_count = 0
            early_stop = False
            record_iter = iter(execution_records)
            with ThreadPoolExecutor(max_workers=max(1, parallel)) as executor:
                for _ in range(min(parallel, len(execution_records))):
                    record = next(record_iter, None)
                    if record is None:
                        break
                    call_hooks("before_scenario", record['id'])
                    print_scenario_start(record['id'], verbose=verbose, color_enabled=color_enabled)
                    fut = executor.submit(_run_scenario, record, verbose, roles_path_resolved)
                    futures[fut] = record

                while futures:
                    for fut in as_completed(list(futures)):
                        record = futures.pop(fut)
                        result_data = fut.result()
                        if verbose > 0:
                            for line in result_data['output_lines']:
                                click.echo(line)
                        if result_data.get('error_message'):
                            click.echo(click.style(result_data['error_message'], fg='red'))
                        if result_data['return_code'] == 0:
                            click.echo(
                                click.style(
                                    f"    Scenario {result_data['id']} completed successfully.",
                                    fg='green',
                                )
                            )
                        else:
                            click.echo(
                                click.style(
                                    f"    Scenario {result_data['id']} failed with return code {result_data['return_code']}.",
                                    fg='red',
                                )
                            )
                        print_scenario_result(
                            result_data['id'],
                            result_data['status'],
                            result_data['duration'],
                            verbose=verbose,
                            color_enabled=color_enabled,
                        )
                        scenario_results_list.append(
                            {
                                'id': result_data['id'],
                                'status': result_data['status'],
                                'duration': result_data['duration'],
                                'return_code': result_data['return_code'],
                            }
                        )
                        update_scenario_status(cache_data, result_data['id'], result_data['status'])
                        call_hooks("after_scenario", result_data['id'], result_data['status'])

                        if result_data['status'].lower() == 'failed' or result_data['return_code'] != 0:
                            failure_count += 1

                        if fail_fast or (maxfail > 0 and failure_count >= maxfail):
                            click.echo(click.style(f"Early termination triggered after {failure_count} failure(s).", fg='yellow'))
                            for pfut, prec in futures.items():
                                pfut.cancel()
                                print_scenario_result(prec['id'], 'skipped', None, verbose=verbose, color_enabled=color_enabled)
                                scenario_results_list.append({'id': prec['id'], 'status': 'skipped', 'duration': None, 'return_code': 0})
                                update_scenario_status(cache_data, prec['id'], 'skipped')
                                call_hooks('after_scenario', prec['id'], 'skipped')
                            early_stop = True
                            futures.clear()
                            break

                        next_record = next(record_iter, None)
                        if next_record is not None:
                            call_hooks("before_scenario", next_record['id'])
                            print_scenario_start(next_record['id'], verbose=verbose, color_enabled=color_enabled)
                            new_fut = executor.submit(_run_scenario, next_record, verbose, roles_path_resolved)
                            futures[new_fut] = next_record
                    if early_stop:
                        break
        finally:
            click.echo("\nSaving test results to cache...")
            try:
                save_cache(cache_data, str(_PROJECT_ROOT))
                if verbose > 0:
                    click.echo(click.style("Cache saved successfully.", fg='green'))
            except (IOError, OSError) as e_cache_final:
                click.echo(click.style(f"Warning: Failed to save cache after test execution: {e_cache_final}", fg="yellow"), err=True)
                # Do not exit here; proceed to report generation and final exit code determination

        overall_end_time = time.monotonic()
        total_execution_duration = overall_end_time - overall_start_time
        print_summary_table(
            scenario_results_list,
            overall_duration=total_execution_duration,
            verbose=verbose,
            color_enabled=color_enabled,
        )

        if json_report:
            if verbose > 0:
                click.echo(f"Generating JSON report at: {json_report}")
            try:
                generate_json_report(
                    scenario_results_list, 
                    json_report, 
                    overall_duration=total_execution_duration, 
                    verbose=verbose
                )
            except (IOError, OSError) as e_report_json:
                click.echo(click.style(f"Warning: Failed to generate JSON report at '{json_report}': {e_report_json}", fg="yellow"), err=True)

        if md_report:
            if verbose > 0:
                click.echo(f"Generating Markdown report at: {md_report}")
            try:
                generate_markdown_report(
                    scenario_results_list,
                    md_report,
                    overall_duration=total_execution_duration,
                    verbose=verbose
                )
            except (IOError, OSError) as e_report_md:
                click.echo(click.style(f"Warning: Failed to generate Markdown report at '{md_report}': {e_report_md}", fg="yellow"), err=True)

        if junit_xml:
            if verbose > 0:
                click.echo(f"Generating JUnit XML report at: {junit_xml}")
            try:
                generate_junit_xml_report(
                    scenario_results_list,
                    junit_xml,
                    overall_duration=total_execution_duration,
                    verbose=verbose,
                )
            except (IOError, OSError) as e_report_xml:
                click.echo(
                    click.style(
                        f"Warning: Failed to generate JUnit XML report at '{junit_xml}': {e_report_xml}",
                        fg="yellow",
                    ),
                    err=True,
                )

        # Determine final exit code based on test results
        # This part is reached only if scenarios_to_run was not empty and tests were attempted.
        final_exit_code = 0
        if not scenario_results_list: # Should not happen if scenarios_to_run was populated, but as a safeguard
            click.echo(click.style("Warning: No test results were recorded.", fg='yellow'), err=True)
            final_exit_code = 0 # Or consider it an error? For now, 0 if no results from execution phase.
        elif any(r.get('status', '').lower() == 'failed' or r.get('return_code', 0) != 0 for r in scenario_results_list):
            final_exit_code = 1

        call_hooks("after_run", scenario_results_list)
        ctx.exit(final_exit_code)

    except Exception as e:
        click.echo(click.style(f"An unexpected error occurred in the main run process: {e}", fg="red"), err=True)
        # Attempt to save cache even if an error occurs in the broader run logic
        if 'cache_data' in locals() and 'save_cache' in globals():
            click.echo("Attempting to save cache due to error...")
            try:
                save_cache(cache_data, str(_PROJECT_ROOT))
            except (IOError, OSError) as e_cache:
                click.echo(click.style(f"Critical: Failed to save cache during error handling: {e_cache}", fg="red"), err=True)
        ctx.exit(3)

@cli.command('clear-cache')
def clear_cache():
    """Clear the Molecule test results cache."""
    cache_file_path = _PROJECT_ROOT / CACHE_FILENAME
    try:
        if cache_file_path.exists():
            os.remove(cache_file_path)
            click.echo(click.style(f"Cache file '{cache_file_path}' cleared successfully.", fg='green'))
        else:
            click.echo(click.style(f"Cache file '{cache_file_path}' not found. Nothing to clear.", fg='yellow'))
    except OSError as e:
        click.echo(click.style(f"Error clearing cache file '{cache_file_path}': {e}", fg='red'), err=True)

@cli.command('show-cache')
def show_cache():
    """Show the contents of the Molecule test results cache."""
    cache_data = load_cache(str(_PROJECT_ROOT)) 
    
    if not cache_data or not cache_data.get('scenarios'):
        click.echo(click.style("Cache is empty or does not exist.", fg='yellow'))
        # Optionally, show default empty structure details
        # empty_cache = get_empty_cache_structure()
        # click.echo(f"Default cache version: {empty_cache['moltest_version']}")
        # click.echo(f"Last run (default): {empty_cache['last_run']}")
        return

    click.echo(click.style("Current Test Cache Contents:", bold=True))
    click.echo(f"  Cache Version: {cache_data.get('moltest_version', 'N/A')}")
    click.echo(f"  Last Run: {cache_data.get('last_run', 'N/A')}")

    scenarios = cache_data.get('scenarios', {})
    if scenarios:
        click.echo(click.style("  Cached Scenarios:", underline=True))
        for scenario_id, status_details in scenarios.items():
            # Compatibility for old cache format (just status string) and new (dict with status and timestamp)
            if isinstance(status_details, dict):
                status = status_details.get('status', 'unknown')
                timestamp = status_details.get('timestamp', 'N/A')
                click.echo(f"    - ID: {scenario_id}, Status: {status}, Timestamp: {timestamp}")
            else: 
                click.echo(f"    - ID: {scenario_id}, Status: {status_details}")
    else:
        click.echo(click.style("  No scenarios found in cache.", fg='yellow'))

if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nProcess interrupted by user.")
        # Exit with a status code 130 for Ctrl+C
        sys.exit(130)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        # import sys
        # sys.exit(1)
