from pathlib import Path
from subprocess import run
from typing import Dict, Union, Callable

import pytest
from dunamai import Version

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


@pytest.mark.parametrize("with_v", [True, False])
@pytest.mark.parametrize("version", [Version("0.1.2"), Version("1", stage=("a", 2))])
def test_git(temp_tree: TempTreeCB, has_src, with_v, version):
    src_path = Path("git_mod.py")
    content = {src_path: "print('hello')\n"}
    if has_src:
        src_path = Path("src") / src_path
        content = dict(src=content)
    with temp_tree(content) as package:
        with get_version.working_dir(package):

            def add_and_commit(msg: str):
                run(f"git add {src_path}".split(), check=True)
                run([*"git commit -m".split(), msg], check=True)

            run("git init".split(), check=True)
            add_and_commit("initial")
            run(f"git tag {'v' if with_v else ''}{version}".split(), check=True)
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
            )
            == v
        )

        parent = (package / "src") if has_src else package
        v = get_version.get_version(parent / "git_mod.py")
        assert f"{version}.post1.dev0+{hash}.dirty" == v


def test_dir(temp_tree: TempTreeCB, has_src):
    dirname = "dir_mod-0.1.3+dirty"
    content = {"dir_mod.py": "print('hi!')\n"}
    if has_src:
        content = dict(src=content)
    spec = {dirname: content}
    with temp_tree(spec) as package:
        v = get_version.get_version_from_dirname("dir_mod", package / dirname)
        assert "0.1.3+dirty" == v

        parent = (package / dirname / "src") if has_src else (package / dirname)
        v = get_version.get_version(parent / "dir_mod.py")
        assert "0.1.3+dirty" == v


def test_dir_dash(temp_tree: TempTreeCB):
    dirname = "dir-two-0.1"
    spec = {dirname: {"dir_two.py": "print('hi!')\n"}}
    with temp_tree(spec) as package:
        v = get_version.get_version_from_dirname("dir-two", package / dirname)
        assert "0.1" == v

        v = get_version.get_version(package / dirname / "dir_two.py")
        assert "0.1" == v


def test_metadata():
    expected = pytest.__version__

    v = get_version.get_version_from_metadata("pytest")
    assert expected == v

    v = get_version.get_version("pytest")
    assert expected == v

    v = get_version.get_version(Path(pytest.__file__))
    assert expected == v
