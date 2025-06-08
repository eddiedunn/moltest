import importlib
from click.testing import CliRunner

from moltest.cli import cli


def test_hooks_execute(tmp_path, mocker, monkeypatch):
    plugin_path = tmp_path / "sample_plugin.py"
    plugin_path.write_text(
        """
Events = []

def before_run(ctx):
    Events.append('before_run')

def before_scenario(sid):
    Events.append(f'before:{sid}')

def after_scenario(sid, status):
    Events.append(f'after:{sid}:{status}')

def after_run(results):
    Events.append('after_run')
"""
    )
    monkeypatch.syspath_prepend(tmp_path)

    mocker.patch('moltest.cli.discover_scenarios', return_value=[
        {'id': 'role:test', 'scenario_name': 'default', 'execution_path': '/fake/path'}
    ])
    mocker.patch('moltest.cli.load_cache', return_value={'moltest_version': '0.1.0', 'last_run': '', 'scenarios': {}})
    mocker.patch('moltest.cli.save_cache')
    mocker.patch('moltest.cli.print_scenario_start')
    mocker.patch('moltest.cli.print_scenario_result')
    mocker.patch('moltest.cli.print_summary_table')
    mocker.patch('click.core.Context.exit', side_effect=lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
    mocker.patch('moltest.cli.check_dependencies')
    mocker.patch('moltest.cli.click.prompt', return_value='roles')
    mocker.patch('moltest.cli.generate_json_report')
    mocker.patch('moltest.cli.generate_markdown_report')

    monkeypatch.setattr('moltest.cli.load_config', lambda: {'plugins': ['sample_plugin'], 'roles_path': 'roles'})
    monkeypatch.setattr('importlib.metadata.entry_points', lambda group=None: [])

    class DummyProc:
        def __init__(self, *a, **k):
            self.returncode = 0
            self.stdout = []
        def __enter__(self):
            return self
        def __exit__(self, exc, val, tb):
            pass
        def wait(self):
            return 0

    mocker.patch('moltest.cli.subprocess.Popen', return_value=DummyProc())

    runner = CliRunner()
    result = runner.invoke(cli, ['run'])
    assert result.exit_code == 0

    plugin = importlib.import_module('sample_plugin')
    assert plugin.Events[0] == 'before_run'
    assert 'before:role:test' in plugin.Events
    assert 'after:role:test:passed' in plugin.Events or 'after:role:test:failed' in plugin.Events
    assert plugin.Events[-1] == 'after_run'
