import sys
print(f"DEBUG: pytest sys.executable: {sys.executable}")
print(f"DEBUG: pytest sys.path: {sys.path}")
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
    mocker.patch('click.core.Context.exit', side_effect=lambda self, code=0: (_ for _ in ()).throw(SystemExit(code)))
    # Skip dependency checks
    mocker.patch('moltest.cli.check_dependencies')
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
    """Test that output is streamed line-by-line when verbose > 0."""
    mock_echo = mock_dependencies  # Get the patched click.echo from mock_dependencies

    # Configure the mock Popen process behavior for this test
    mock_popen.simulated_stdout_lines = ["First output line from command\n", "Second output line\n"]
    mock_popen.simulated_stderr_lines = ["Error message from command\n"] # Will be merged
    mock_popen.returncode_to_simulate = 0

    # Invoke the 'run' command with the verbose flag
    result = runner.invoke(cli, ['run', '-v'])

    assert result.exit_code == 0, f"CLI command failed: {result.output}"

    # Verify that click.echo was called with the streamed lines
    # The 'run' command prefixes streamed lines with "      "
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
    assert mock_popen.stderr_pipe_received == subprocess.STDOUT # Check stderr merging
    assert mock_popen.text_mode_received is True
    assert mock_popen.bufsize_arg_received == 1
    
    # Verify proc.wait() was NOT called because it was verbose
    assert mock_popen.wait_called is False


def test_run_no_stream_not_verbose(runner, mock_dependencies, mock_popen):
    """Test that output is NOT streamed if verbose is 0, and proc.wait() is called."""
    mock_echo = mock_dependencies
    
    mock_popen.returncode_to_simulate = 0

    result = runner.invoke(cli, ['run']) # No -v flag

    assert result.exit_code == 0, f"CLI command failed: {result.output}"

    # Assert that no simulated output lines were echoed
    actual_calls = mock_echo.call_args_list
    for call_args in actual_calls:
        # Check the first argument of the call, which is the string passed to click.echo
        assert "Simulated" not in call_args[0][0]
        assert "First output line" not in call_args[0][0]

    # Verify proc.wait() WAS called
    assert mock_popen.wait_called is True
    
    # Verify Popen was still called with correct cwd etc.
    assert mock_popen.cwd_received == Path('/fake/path/role_alpha')


# TODO: Add more tests:
# - test_run_uses_correct_cwd_multiple_scenarios() (if discover_scenarios returns multiple)
# - test_run_handles_command_failure_return_code()
# - test_run_handles_popen_exception() (e.g., FileNotFoundError if Popen itself fails)