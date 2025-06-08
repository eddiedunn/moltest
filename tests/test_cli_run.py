import pytest
from unittest import mock
import subprocess  # For subprocess.STDOUT
from click.testing import CliRunner
from pathlib import Path

# Assuming 'cli' is the Click group and 'run' is a command on it
from moltest.cli import cli


# --- Mock Popen Process ---
class MockPopenProcess:
    def __init__(self, command_parts, stdout_pipe, stderr_pipe, text_mode, bufsize_arg, cwd_arg):
        # Arguments Popen is called with
        self.command_parts_received = command_parts
        self.stdout_pipe_received = stdout_pipe
        self.stderr_pipe_received = stderr_pipe
        self.text_mode_received = text_mode
        self.bufsize_arg_received = bufsize_arg
        self.cwd_received = cwd_arg
        
        # Configurable behavior for the test
        self.simulated_stdout_lines = ["Simulated stdout line 1\n", "Simulated stdout line 2\n"]
        self.simulated_stderr_lines = ["Simulated stderr line 1\n"] # Used if stderr is not STDOUT
        self.returncode_to_simulate = 0
        self.wait_called = False
        # Track each invocation of Popen when the same instance is reused
        self.call_history = []

        # stdout stream simulation
        if self.stderr_pipe_received == subprocess.STDOUT:
            self.stdout = iter(self.simulated_stdout_lines + self.simulated_stderr_lines)
        else:
            self.stdout = iter(self.simulated_stdout_lines)
            # If you need to test stderr separately when not merged:
            # self.stderr = iter(self.simulated_stderr_lines) 

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # Nothing to clean up in this mock

    def wait(self):
        self.wait_called = True
        # Consume any remaining stdout, as proc.wait() would ensure the process is finished
        for _ in self.stdout:
            pass
        return self.returncode_to_simulate

    @property
    def returncode(self):
        # In a real process, returncode is available after the process finishes.
        # Our mock ensures stdout is consumed (either by iteration or by wait())
        # before this would typically be accessed.
        return self.returncode_to_simulate


# --- Pytest Fixtures ---
@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_dependencies(mocker):
    """Mocks external dependencies of the 'run' command."""
    # Mock scenario discovery
    mocker.patch('moltest.cli.discover_scenarios', return_value=[
        {'id': 'test-scenario-alpha', 'scenario_name': 'default', 'execution_path': '/fake/path/role_alpha'}
    ])
    # Mock cache functions
    mocker.patch('moltest.cli.load_cache', return_value={'moltest_version': '0.1.0', 'last_run': '', 'scenarios': {}})
    mocker.patch('moltest.cli.save_cache')
    # Mock printing functions to avoid console noise during tests
    mocker.patch('moltest.cli.print_scenario_start')
    mocker.patch('moltest.cli.print_scenario_result')
    mocker.patch('moltest.cli.print_summary_table')
    # Avoid Click's Exit exception being caught by the CLI
    mocker.patch('click.core.Context.exit', side_effect=lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
    # Skip dependency checks
    mocker.patch('moltest.cli.check_dependencies')
    mocker.patch('moltest.cli.click.prompt', return_value='roles')
    # Prevent actual report generation during tests
    mocker.patch('moltest.cli.generate_json_report')
    mocker.patch('moltest.cli.generate_markdown_report')
    mocker.patch('moltest.cli.generate_junit_xml_report')
    # Patch click.echo to capture its output for assertions
    mocked_echo = mocker.patch('moltest.cli.click.echo')
    return mocked_echo

@pytest.fixture
def mock_popen(mocker):
    """
    Patches subprocess.Popen to return a configurable MockPopenProcess instance.
    The fixture returns the MockPopenProcess instance itself, so tests can configure it
    (e.g., set simulated_stdout_lines, returncode_to_simulate) before invoking the CLI
    and inspect its attributes (e.g., cwd_received, wait_called) afterwards.
    """
    # This is the instance that will be configured by the test and returned by Popen
    # Provide some default init args for MockPopenProcess, Popen call will overwrite them.
    mock_proc_instance = MockPopenProcess([], None, None, None, None, None)

    def side_effect_for_popen(*args, **kwargs):
        # Update the mock_proc_instance with the actual arguments Popen was called with
        mock_proc_instance.command_parts_received = args[0] # command_parts is the first arg
        mock_proc_instance.stdout_pipe_received = kwargs.get('stdout')
        mock_proc_instance.stderr_pipe_received = kwargs.get('stderr')
        mock_proc_instance.text_mode_received = kwargs.get('text')
        mock_proc_instance.bufsize_arg_received = kwargs.get('bufsize')
        mock_proc_instance.cwd_received = kwargs.get('cwd')

        # Record this call so tests can verify multiple invocations
        mock_proc_instance.call_history.append({
            'args': args[0],
            'cwd': kwargs.get('cwd')
        })

        # Re-initialize the stdout iterator based on how Popen was called (stderr redirection)
        if mock_proc_instance.stderr_pipe_received == subprocess.STDOUT:
            mock_proc_instance.stdout = iter(mock_proc_instance.simulated_stdout_lines + mock_proc_instance.simulated_stderr_lines)
        else:
            mock_proc_instance.stdout = iter(mock_proc_instance.simulated_stdout_lines)
        
        mock_proc_instance.wait_called = False # Reset for each Popen call if necessary
        return mock_proc_instance

    mocker.patch('moltest.cli.subprocess.Popen', side_effect=side_effect_for_popen)
    return mock_proc_instance


# --- Test Cases ---
def test_run_streams_output_verbose(runner, mock_dependencies, mock_popen):
    """Output should be streamed line-by-line when verbose flag is used."""
    mock_echo = mock_dependencies  # Get the patched click.echo from mock_dependencies

    # Configure the mock Popen process behavior for this test
    mock_popen.simulated_stdout_lines = ["First output line from command\n", "Second output line\n"]
    mock_popen.simulated_stderr_lines = ["Error message from command\n"] # Will be merged
    mock_popen.returncode_to_simulate = 0

    # Invoke the 'run' command with verbosity
    result = runner.invoke(cli, ['run', '-v'])

    assert result.exit_code == 0, f"CLI command failed: {result.output}"

    # Verify that click.echo was called with the streamed lines
    # Lines are prefixed with six spaces
    expected_echo_calls = [
        mock.call("      First output line from command"),
        mock.call("      Second output line"),
        mock.call("      Error message from command"),
    ]

    # Check if all expected calls are present among the actual calls to click.echo
    # This is a bit lenient as it doesn't check order or exclusivity,
    # but good for a start.
    actual_calls = mock_echo.call_args_list
    for expected_call in expected_echo_calls:
        assert expected_call in actual_calls, f"Expected echo call '{expected_call}' not found in actual calls: {actual_calls}"

    # Verify Popen was called correctly
    assert mock_popen.cwd_received == Path('/fake/path/role_alpha')
    assert mock_popen.stdout_pipe_received == subprocess.PIPE
    assert mock_popen.stderr_pipe_received == subprocess.STDOUT
    assert mock_popen.text_mode_received is True
    assert mock_popen.bufsize_arg_received == 1

    # proc.wait() should not be called
    assert mock_popen.wait_called is False


def test_run_consumes_output_without_verbose(runner, mock_dependencies, mock_popen):
    """Output should not be streamed when no -v flag is provided."""
    mock_echo = mock_dependencies

    mock_popen.simulated_stdout_lines = ["Line A\n", "Line B\n"]
    mock_popen.returncode_to_simulate = 0

    result = runner.invoke(cli, ['run'])

    assert result.exit_code == 0, f"CLI command failed: {result.output}"

    # Ensure the output lines were not echoed
    unwanted_calls = [
        mock.call("      Line A"),
        mock.call("      Line B"),
    ]

    for unwanted_call in unwanted_calls:
        assert unwanted_call not in mock_echo.call_args_list

    # wait() should be called to consume output
    assert mock_popen.wait_called is True

    # cwd should be set to the scenario's execution path
    assert mock_popen.cwd_received == Path('/fake/path/role_alpha')
    assert mock_popen.stderr_pipe_received == subprocess.STDOUT


# TODO: Add more tests:
# - test_run_uses_correct_cwd_multiple_scenarios() (if discover_scenarios returns multiple)
# - test_run_handles_command_failure_return_code()
# - test_run_handles_popen_exception() (e.g., FileNotFoundError if Popen itself fails)
# New fixtures for exit code tests
@pytest.fixture
def mock_dependencies_no_scenarios(mocker):
    """Mocks dependencies with no discovered scenarios."""
    mocker.patch('moltest.cli.discover_scenarios', return_value=[])
    mocker.patch('moltest.cli.load_cache', return_value={'moltest_version': '0.1.0', 'last_run': '', 'scenarios': {}})
    mocker.patch('moltest.cli.save_cache')
    mocker.patch('moltest.cli.print_scenario_start')
    mocker.patch('moltest.cli.print_scenario_result')
    mocker.patch('moltest.cli.print_summary_table')
    mocker.patch('click.core.Context.exit', side_effect=lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
    mocker.patch('moltest.cli.check_dependencies')
    mocker.patch('moltest.cli.click.prompt', return_value='roles')
    mocker.patch('moltest.cli.generate_junit_xml_report')
    mocked_echo = mocker.patch('moltest.cli.click.echo')
    return mocked_echo

@pytest.fixture
def mock_dependencies_multi(mocker):
    """Mocks dependencies returning two scenarios."""
    mocker.patch('moltest.cli.discover_scenarios', return_value=[
        {'id': 'role1:alpha', 'scenario_name': 'alpha', 'execution_path': '/fake/path/role1'},
        {'id': 'role2:beta', 'scenario_name': 'beta', 'execution_path': '/fake/path/role2'},
    ])
    mocker.patch('moltest.cli.load_cache', return_value={'moltest_version': '0.1.0', 'last_run': '', 'scenarios': {}})
    mocker.patch('moltest.cli.save_cache')
    mocker.patch('moltest.cli.print_scenario_start')
    mocker.patch('moltest.cli.print_scenario_result')
    mocker.patch('moltest.cli.print_summary_table')
    mocker.patch('click.core.Context.exit', side_effect=lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
    mocker.patch('moltest.cli.check_dependencies')
    mocker.patch('moltest.cli.click.prompt', return_value='roles')
    mocker.patch('moltest.cli.generate_junit_xml_report')
    mocked_echo = mocker.patch('moltest.cli.click.echo')
    return mocked_echo


@pytest.fixture
def mock_dependencies_tagged(mocker):
    """Mocks a single scenario with a 'slow' tag."""
    mocker.patch('moltest.cli.discover_scenarios', return_value=[
        {'id': 'role1:alpha', 'scenario_name': 'alpha', 'execution_path': '/fake/path/role1', 'tags': ['slow']},
    ])
    mocker.patch('moltest.cli.load_cache', return_value={'moltest_version': '0.1.0', 'last_run': '', 'scenarios': {}})
    mocker.patch('moltest.cli.save_cache')
    mocker.patch('moltest.cli.print_scenario_start')
    mocker.patch('moltest.cli.print_scenario_result')
    mocker.patch('moltest.cli.print_summary_table')
    mocker.patch('click.core.Context.exit', side_effect=lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
    mocker.patch('moltest.cli.check_dependencies')
    mocker.patch('moltest.cli.click.prompt', return_value='roles')
    mocker.patch('moltest.cli.generate_junit_xml_report')
    mocked_echo = mocker.patch('moltest.cli.click.echo')
    return mocked_echo


@pytest.fixture
def mock_dependencies_params(mocker):
    """Mocks a scenario with parameter sets."""
    mocker.patch('moltest.cli.discover_scenarios', return_value=[
        {
            'id': 'role1:alpha',
            'scenario_name': 'alpha',
            'execution_path': '/fake/path/role1',
            'parameters': [
                {'id': 'set1', 'vars': {'FOO': 'A'}},
                {'id': 'set2', 'vars': {'FOO': 'B'}},
            ],
        }
    ])
    mocker.patch('moltest.cli.load_cache', return_value={'moltest_version': '0.1.0', 'last_run': '', 'scenarios': {}})
    mocker.patch('moltest.cli.save_cache')
    start = mocker.patch('moltest.cli.print_scenario_start')
    result = mocker.patch('moltest.cli.print_scenario_result')
    mocker.patch('moltest.cli.print_summary_table')
    mocker.patch('click.core.Context.exit', side_effect=lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
    mocker.patch('moltest.cli.check_dependencies')
    mocker.patch('moltest.cli.click.prompt', return_value='roles')
    mocker.patch('moltest.cli.generate_junit_xml_report')
    echo = mocker.patch('moltest.cli.click.echo')
    return {'echo': echo, 'start': start, 'result': result}


@pytest.fixture
def mock_dependencies_three(mocker):
    """Mocks three scenarios for maxfail testing."""
    mocker.patch('moltest.cli.discover_scenarios', return_value=[
        {'id': 'role1:alpha', 'scenario_name': 'alpha', 'execution_path': '/fake/path/role1'},
        {'id': 'role2:beta', 'scenario_name': 'beta', 'execution_path': '/fake/path/role2'},
        {'id': 'role3:gamma', 'scenario_name': 'gamma', 'execution_path': '/fake/path/role3'},
    ])
    mocker.patch('moltest.cli.load_cache', return_value={'moltest_version': '0.1.0', 'last_run': '', 'scenarios': {}})
    mocker.patch('moltest.cli.save_cache')
    mocker.patch('moltest.cli.print_scenario_start')
    mocker.patch('moltest.cli.print_scenario_result')
    mocker.patch('moltest.cli.print_summary_table')
    mocker.patch('click.core.Context.exit', side_effect=lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
    mocker.patch('moltest.cli.check_dependencies')
    mocker.patch('moltest.cli.click.prompt', return_value='roles')
    mocker.patch('moltest.cli.generate_junit_xml_report')
    mocked_echo = mocker.patch('moltest.cli.click.echo')
    return mocked_echo


def test_run_exits_when_no_scenarios(runner, mock_dependencies_no_scenarios):
    """CLI exits with code 2 when no scenarios are discovered."""
    result = runner.invoke(cli, ['run'])
    assert result.exit_code == 2


def test_run_failing_scenario_exit_code(runner, mock_dependencies_multi, mock_popen):
    """Failure during scenario execution results in exit code 1."""
    mock_popen.returncode_to_simulate = 1
    result = runner.invoke(cli, ['run'])
    assert result.exit_code == 1


def test_lf_alias_invokes_rerun_failed(runner, mock_dependencies, mock_popen):
    """--lf should behave as an alias for --rerun-failed."""
    result = runner.invoke(cli, ['run', '--lf', '-v'])
    assert result.exit_code == 0
    mock_dependencies.assert_any_call('Rerun failed: True')


def test_f_alias_invokes_rerun_failed(runner, mock_dependencies, mock_popen):
    """-f short option should also trigger rerun-failed."""
    result = runner.invoke(cli, ['run', '-f', '-v'])
    assert result.exit_code == 0
    mock_dependencies.assert_any_call('Rerun failed: True')


def test_no_color_auto_enabled_in_ci(runner, mock_dependencies, mock_popen, monkeypatch):
    """CI environment should force no-color output."""
    monkeypatch.setenv('CI', 'true')
    monkeypatch.setattr('sys.stdout.isatty', lambda: True)
    result = runner.invoke(cli, ['run', '-v'])
    assert result.exit_code == 0
    mock_dependencies.assert_any_call('No color: True')


def test_no_color_flag(runner, mock_dependencies, mock_popen):
    """Explicit --no-color option disables colored output."""
    result = runner.invoke(cli, ['run', '--no-color', '-v'])
    assert result.exit_code == 0
    mock_dependencies.assert_any_call('No color: True')


import click

from moltest.cli import validate_report_path

def test_validate_report_path(tmp_path):
    """validate_report_path rejects wrong extensions and creates parents."""

    @click.command()
    @click.option('--path', callback=lambda ctx, param, val: validate_report_path(ctx, param, val, '.json'))
    def dummy(path):
        click.echo(path)

    runner_local = CliRunner()
    good = tmp_path / 'out' / 'file.json'
    result = runner_local.invoke(dummy, ['--path', str(good)])
    assert result.exit_code == 0
    assert good.parent.exists()

    bad = tmp_path / 'bad.txt'
    result_bad = runner_local.invoke(dummy, ['--path', str(bad)])
    assert result_bad.exit_code == 2
    assert "'.json'" in result_bad.output


def test_default_report_paths(tmp_path, runner, mocker, monkeypatch, mock_popen, mock_dependencies):
    """Using -j or -m without a path should use default filenames."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        monkeypatch.setattr('moltest.cli._PROJECT_ROOT', Path.cwd())
        mock_json = mocker.patch('moltest.cli.generate_json_report')
        mock_md = mocker.patch('moltest.cli.generate_markdown_report')
        mock_xml = mocker.patch('moltest.cli.generate_junit_xml_report')

        result = runner.invoke(cli, ['run', '-j', '-m', '-x'])
        assert result.exit_code == 0

        expected_json = str(Path('moltest_report.json').resolve())
        expected_md = str(Path('moltest_report.md').resolve())
        expected_xml = str(Path('moltest_report.xml').resolve())

        assert mock_json.call_args[0][1] == expected_json
        assert mock_md.call_args[0][1] == expected_md
        assert mock_xml.call_args[0][1] == expected_xml


def test_run_uses_correct_cwd_multiple_scenarios(runner, mock_dependencies_multi, mock_popen):
    """Each scenario should be executed in its own directory."""
    result = runner.invoke(cli, ['run'])
    assert result.exit_code == 0

    cwds = [entry['cwd'] for entry in mock_popen.call_history]
    assert cwds == [Path('/fake/path/role1'), Path('/fake/path/role2')]


def test_run_handles_command_failure_return_code(runner, mock_dependencies, mock_popen):
    """Non-zero return code from Molecule results in exit code 1."""
    mock_popen.returncode_to_simulate = 2
    result = runner.invoke(cli, ['run'])
    assert result.exit_code == 1

    failure_msgs = [c.args[0] for c in mock_dependencies.call_args_list if 'failed with return code' in c.args[0]]
    assert any('failed with return code 2' in msg for msg in failure_msgs)


def test_run_handles_popen_exception(runner, mock_dependencies, monkeypatch):
    """If Popen itself raises an error the CLI still reports failure."""
    def raise_fn(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr('moltest.cli.subprocess.Popen', raise_fn)
    result = runner.invoke(cli, ['run'])
    assert result.exit_code == 1
    error_msgs = [c.args[0] for c in mock_dependencies.call_args_list if 'Error:' in c.args[0]]
    assert any('molecule command not found' in msg for msg in error_msgs)


def test_run_skips_tagged_scenarios(runner, mock_dependencies_tagged, mock_popen):
    """Scenarios with skip tags should not be executed."""
    result = runner.invoke(cli, ['run', '--skip', 'slow'])
    assert result.exit_code == 0
    # No commands should be executed
    assert mock_popen.call_history == []
    echo_msgs = [c.args[0] for c in mock_dependencies_tagged.call_args_list]
    assert any('Skipping role1:alpha' in msg for msg in echo_msgs)


def test_run_parameter_sets(runner, mock_dependencies_params, mock_popen):
    """Each parameter set should trigger a separate Molecule run."""
    result = runner.invoke(cli, ['run'])
    assert result.exit_code == 0

    # Two parameter sets -> two executions
    assert len(mock_popen.call_history) == 2

    starts = [call.args[0] for call in mock_dependencies_params['start'].call_args_list]
    assert 'role1:alpha[set1]' in starts
    assert 'role1:alpha[set2]' in starts


def test_k_expression_filters_scenarios(runner, mock_dependencies_multi, mock_popen):
    """-k expression should filter scenarios by ID."""
    result = runner.invoke(cli, ['run', '-k', 'role1'])
    assert result.exit_code == 0

    # Only the matching scenario should run
    cwds = [entry['cwd'] for entry in mock_popen.call_history]
    assert cwds == [Path('/fake/path/role1')]


def test_k_expression_no_match(runner, mock_dependencies_multi, mock_popen):
    """No scenarios should run if -k expression matches none."""
    result = runner.invoke(cli, ['run', '-k', 'nonexistent'])
    assert result.exit_code == 0
    assert mock_popen.call_history == []
    echo_msgs = [c.args[0] for c in mock_dependencies_multi.call_args_list]
    assert any('No Molecule tests will be run' in m for m in echo_msgs)


def test_parallel_option_uses_executor(runner, mock_dependencies_multi, mock_popen, mocker):
    """--parallel should run scenarios via ThreadPoolExecutor."""

    executors = []

    class DummyFuture:
        def __init__(self, res):
            self._res = res

        def result(self):
            return self._res

    class DummyExecutor:
        def __init__(self, max_workers=None):
            self.max_workers = max_workers
            self.submitted = []
            executors.append(self)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def submit(self, fn, *args, **kwargs):
            res = fn(*args, **kwargs)
            fut = DummyFuture(res)
            self.submitted.append(fut)
            return fut

    def dummy_as_completed(fs):
        for f in fs:
            yield f

    mocker.patch('moltest.cli.ThreadPoolExecutor', DummyExecutor)
    mocker.patch('moltest.cli.as_completed', dummy_as_completed)

    result = runner.invoke(cli, ['run', '--parallel', '2'])
    assert result.exit_code == 0

    assert executors[0].max_workers == 2
    assert len(executors[0].submitted) == 2


def test_fail_fast_stops_after_first_failure(runner, mock_dependencies_multi, mock_popen):
    """--fail-fast should stop execution after the first failing scenario."""
    mock_popen.returncode_to_simulate = 1
    result = runner.invoke(cli, ['run', '--fail-fast'])
    assert result.exit_code == 1
    assert len(mock_popen.call_history) == 1
    echo_msgs = [c.args[0] for c in mock_dependencies_multi.call_args_list]
    assert any('Early termination triggered' in m for m in echo_msgs)


def test_maxfail_limits_failures(runner, mock_dependencies_three, mock_popen):
    """--maxfail should stop after the specified number of failures."""
    mock_popen.returncode_to_simulate = 1
    result = runner.invoke(cli, ['run', '--maxfail', '2'])
    assert result.exit_code == 1
    assert len(mock_popen.call_history) == 2
    echo_msgs = [c.args[0] for c in mock_dependencies_three.call_args_list]
    assert any('Early termination triggered' in m for m in echo_msgs)

