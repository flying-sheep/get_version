from pathlib import Path
from typing import Dict, Union, Callable

import pytest
from testpath import MockCommand

import get_version

Desc = Dict[str, Union["Desc", str, bytes]]
TempTreeCB = Callable[[Desc], Path]


mock_git_describe = """\
#!/usr/bin/env python3
import sys
if "--show-toplevel" in sys.argv:
    print("{}")
else:
    print("v0.1.2-3-gfefe123-dirty")
"""


@pytest.fixture(params=[True, False], ids=["src", "plain"])
def has_src(request) -> bool:
    return request.param


def test_git(temp_tree: TempTreeCB, has_src):
    content = {"git_mod.py": "print('hello')\n"}
    if has_src:
        content = dict(src=content)
    spec = {".git": {}, **content}
    with temp_tree(spec) as package, MockCommand(
        "git", mock_git_describe.format(package)
    ):
        v = get_version.get_version_from_git(package)
        assert get_version.Version("0.1.2", "3", ["fefe123", "dirty"]) == v

        parent = (package / "src") if has_src else package
        v = get_version.get_version(parent / "git_mod.py")
        assert "0.1.2.dev3+fefe123.dirty" == v


def test_dir(temp_tree: TempTreeCB, has_src):
    dirname = "dir_mod-0.1.3+dirty"
    content = {"dir_mod.py": "print('hi!')\n"}
    if has_src:
        content = dict(src=content)
    spec = {dirname: content}
    with temp_tree(spec) as package:
        v = get_version.get_version_from_dirname("dir_mod", package / dirname)
        assert get_version.Version("0.1.3", None, ["dirty"]) == v

        parent = (package / dirname / "src") if has_src else (package / dirname)
        v = get_version.get_version(parent / "dir_mod.py")
        assert "0.1.3+dirty" == v


def test_dir_dash(temp_tree: TempTreeCB):
    dirname = "dir-two-0.1"
    spec = {dirname: {"dir_two.py": "print('hi!')\n"}}
    with temp_tree(spec) as package:
        v = get_version.get_version_from_dirname("dir-two", package / dirname)
        assert get_version.Version("0.1", None, []) == v

        v = get_version.get_version(package / dirname / "dir_two.py")
        assert "0.1" == v


def test_metadata():
    expected = pytest.__version__

    v = get_version.get_version_from_metadata("pytest")
    assert get_version.Version(expected, None, []) == v

    v = get_version.get_version("pytest")
    assert expected == v

    v = get_version.get_version(Path(pytest.__file__))
    assert expected == v
