import re
from pathlib import Path
from subprocess import run
from typing import Dict, Union, Callable

import pytest
from dunamai import Version

import get_version
from get_version import NoVersionFound

Desc = Dict[str, Union["Desc", str, bytes]]
TempTreeCB = Callable[[Desc], Path]


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


@pytest.mark.parametrize("version", ["0.1.3+dirty", "1.2.post29.dev0+41ced3e.dirty"])
@pytest.mark.parametrize("distname", ["dir_mod", "dir-mod", "mod"])
def test_dir(temp_tree: TempTreeCB, has_src, version, distname):
    content = {"dir_mod.py": "print('hi!')\n"}
    if has_src:
        content = dict(src=content)
    dirname = f"{distname}-{version}"
    spec = {dirname: content}
    with temp_tree(spec) as package:
        v = get_version.get_version_from_dirname(package / dirname)
        assert version == v

        parent = (package / dirname / "src") if has_src else (package / dirname)
        v = get_version.get_version(parent / "dir_mod.py")
        assert version == v


def test_dir_dash(temp_tree: TempTreeCB):
    dirname = "dir-two-0.1"
    spec = {dirname: {"dir_two.py": "print('hi!')\n"}}
    with temp_tree(spec) as package:
        v = get_version.get_version_from_dirname(package / dirname)
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


@pytest.mark.parametrize(
    "gv_fn,path,e_cls,msg",
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
def test_error(temp_tree: TempTreeCB, gv_fn, path, e_cls, msg):
    spec = dict(mod_dev_dir={"mod.py": "print('hi!')\n"})
    with temp_tree(spec) as package:
        with pytest.raises(e_cls, match=msg):
            gv_fn(package / "mod_dev_dir" / path)
