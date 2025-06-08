from pathlib import Path
from click.testing import CliRunner
from moltest.cli import cli

from moltest.cache import CACHE_FILENAME

def test_clear_cache_removes_file(tmp_path, monkeypatch):
    """`clear-cache` deletes existing cache file."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = Path(CACHE_FILENAME)
        cache_file.write_text("{}")
        monkeypatch.setattr('moltest.cli._PROJECT_ROOT', Path.cwd())
        result = runner.invoke(cli, ['clear-cache'])
        assert result.exit_code == 0
        assert not cache_file.exists()


def test_show_cache_when_empty(tmp_path, monkeypatch):
    """`show-cache` reports when no cache exists."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        monkeypatch.setattr('moltest.cli._PROJECT_ROOT', Path.cwd())
        result = runner.invoke(cli, ['show-cache'])
        assert result.exit_code == 0
        assert 'Cache is empty' in result.output

