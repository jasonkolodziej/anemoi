"""Copying a gridded cache to local disk before training (data.cache_localize)."""

from __future__ import annotations

import pytest

from anemoi.cli import main
from anemoi.data.cache_localize import localize_cache


def _cache(root):
    (root / "AL092005").mkdir(parents=True)
    (root / "EP071991").mkdir()
    (root / "AL092005" / "2005082318.npz").write_bytes(b"a" * 100)
    (root / "AL092005" / "2005082400.npz").write_bytes(b"b" * 50)
    (root / "EP071991" / "1991080200.npz").write_bytes(b"c" * 10)
    (root / "_meta.json").write_text('{"nwp_lead_hours": 6}\n')  # GDAS's lead record


def test_copies_every_file_to_the_same_relative_path(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    _cache(src)

    report = localize_cache(src, dst, workers=4)

    assert (report.n_copied, report.n_skipped, report.n_bytes) == (4, 0, 160 + 22)
    for f in src.rglob("*"):
        if f.is_file():
            assert (dst / f.relative_to(src)).read_bytes() == f.read_bytes()


def test_a_rerun_only_fills_gaps(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    _cache(src)
    localize_cache(src, dst)
    (src / "EP071991" / "1991080206.npz").write_bytes(b"d" * 5)

    report = localize_cache(src, dst)

    assert (report.n_copied, report.n_skipped) == (1, 4)


def test_a_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        localize_cache(tmp_path / "nope", tmp_path / "dst")


def test_cli_exits_nonzero_on_failure_so_the_entrypoint_falls_back(tmp_path, capsys):
    argv = ["cache-localize", "--src", str(tmp_path / "nope"), "--dst", str(tmp_path / "d")]
    assert main(argv) == 1
    assert "failed" in capsys.readouterr().out


def test_cli_reports_what_it_copied(tmp_path, capsys):
    src = tmp_path / "src"
    _cache(src)
    assert main(["cache-localize", "--src", str(src), "--dst", str(tmp_path / "dst")]) == 0
    assert "4 copied" in capsys.readouterr().out


def test_a_directory_that_cant_be_listed_fails_the_copy(tmp_path, monkeypatch):
    """A storm directory the bucket mount fails to list must fail the copy
    (so the entrypoint trains from /cache), not drop that storm silently."""
    import os

    src = tmp_path / "src"
    _cache(src)
    real_scandir = os.scandir

    def flaky_scandir(path="."):
        if str(path).endswith("EP071991"):
            raise PermissionError(13, "listing failed", str(path))
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", flaky_scandir)
    with pytest.raises(PermissionError):
        localize_cache(src, tmp_path / "dst")
