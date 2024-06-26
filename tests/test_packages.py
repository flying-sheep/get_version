from __future__ import annotations

import os
import re
from contextlib import contextmanager
from pathlib import Path
from subprocess import run
from typing import TYPE_CHECKING

import pytest
from dunamai import Version

import get_version
from get_version import NoVersionFound


if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from get_version.testing import Desc, TempTreeCB


@contextmanager
def chdir(dir_: os.PathLike | None = None) -> Generator[None, None, None]:
    curdir = os.getcwd()
    try:
        if dir_ is not None:
            os.chdir(dir_)
        yield
    finally:
        os.chdir(curdir)


@pytest.fixture(params=[True, False], ids=["src", "plain"])
def has_src(request: pytest.FixtureRequest) -> bool:
    return request.param


@pytest.mark.parametrize("with_v", [True, False], ids=["with_v", "without_v"])
@pytest.mark.parametrize("version", [Version("0.1.2"), Version("1", stage=("a", 2))])
def test_git(
    temp_tree: TempTreeCB, has_src: bool, with_v: bool, version: Version
) -> None:
    src_path = Path("git_mod.py")
    content: Desc = {src_path: "print('hello')\n"}
    if has_src:
        src_path = Path("src") / src_path
        content = dict(src=content)
    package = temp_tree(content)
    with chdir(package):

        def add_and_commit(msg: str) -> None:
            run(["git", "add", str(src_path)], check=True)
            run(["git", "commit", "-m", msg], check=True)

        run(["git", "init", "-b", "main"], check=True)
        run(["git", "config", "user.name", "A U Thor"], check=True)
        run(["git", "config", "user.email", "author@example.com"], check=True)
        add_and_commit("initial")
        run(["git", "tag", f"{'v' if with_v else ''}{version}"], check=True)
        src_path.write_text("print('modified')")
        add_and_commit("modified")
        hash = run(
            "git rev-parse --short HEAD".split(),
            capture_output=True,
            encoding="ascii",
        ).stdout.strip()
        src_path.write_text("print('dirty')")

    v = get_version.dunamai_get_from_vcs(package)
    assert (
        Version(
            version.base,
            stage=(version.stage, version.revision),
            distance=1,
            commit=hash,
            dirty=True,
            branch="main",
            timestamp=v.timestamp,  # Fake it, not important
        )
        == v
    )

    parent = (package / "src") if has_src else package
    v_str = get_version.get_version(parent / "git_mod.py")
    assert f"{version}.post1.dev0+{hash}.dirty" == v_str


@pytest.mark.parametrize("version", ["0.1.3+dirty", "1.2.post29.dev0+41ced3e.dirty"])
@pytest.mark.parametrize("distname", ["dir_mod", "dir-mod", "mod"])
def test_dir(temp_tree: TempTreeCB, has_src: bool, version: str, distname: str) -> None:
    content: Desc = {"dir_mod.py": "print('hi!')\n"}
    if has_src:
        content = dict(src=content)
    dirname = f"{distname}-{version}"
    spec: Desc = {dirname: content}
    package = temp_tree(spec)
    v = get_version.get_version_from_dirname(package / dirname)
    assert version == v

    parent = (package / dirname / "src") if has_src else (package / dirname)
    v = get_version.get_version(parent / "dir_mod.py")
    assert version == v


def test_dir_dash(temp_tree: TempTreeCB) -> None:
    dirname = "dir-two-0.1"
    spec: Desc = {dirname: {"dir_two.py": "print('hi!')\n"}}
    package = temp_tree(spec)
    v = get_version.get_version_from_dirname(package / dirname)
    assert "0.1" == v

    v = get_version.get_version(package / dirname / "dir_two.py")
    assert "0.1" == v


def test_metadata() -> None:
    expected = pytest.__version__

    v = get_version.get_version_from_metadata("pytest")
    assert expected == v

    v = get_version.get_version("pytest")
    assert expected == v

    v = get_version.get_version(Path(pytest.__file__))
    assert expected == v


@pytest.mark.parametrize(
    ("gv_fn", "path", "e_cls", "msg"),
    [
        (
            get_version.get_version_from_dirname,
            ".",
            NoVersionFound,
            "No version found via Directory",
        ),
        (
            get_version.get_version,
            ".",
            ValueError,
            r"neither the name of an installed module nor the path to a \.py file",
        ),
        (
            get_version.get_version,
            "mod.py",
            NoVersionFound,
            re.compile(
                r"^No version found:\n"
                r"- Directory name:.*mod_dev_dir” does not contain a valid version\.\n"
                r"- VCS: could not find VCS from directory.*mod_dev_dir”\.\n"
                r"- Package metadata: could not find distribution “mod”\.$"
            ),
        ),
    ],
)
def test_error(
    temp_tree: TempTreeCB,
    gv_fn: Callable[[Path], object],
    path: str,
    e_cls: type[Exception],
    msg: str,
) -> None:
    spec: Desc = dict(mod_dev_dir={"mod.py": "print('hi!')\n"})
    package = temp_tree(spec)
    with pytest.raises(e_cls, match=msg):
        gv_fn(package / "mod_dev_dir" / path)
