"""Local walk rules for `share post`."""

from pathlib import Path

import pytest

from share_cli.walk import SecretFileError, walk_files


def test_walk_skips_git_and_hashes(tmp_path: Path):
    (tmp_path / "index.html").write_text("<p>hi</p>")
    git = tmp_path / ".git"
    git.mkdir()
    (git / "config").write_text("secret")
    files = walk_files(tmp_path)
    paths = {f["path"] for f in files}
    assert paths == {"index.html"}
    assert files[0]["sha256"]


def test_walk_refuses_env(tmp_path: Path):
    (tmp_path / ".env").write_text("TOKEN=nope")
    with pytest.raises(SecretFileError):
        walk_files(tmp_path)
    files = walk_files(tmp_path, force_secrets=True)
    assert files[0]["path"] == ".env"
