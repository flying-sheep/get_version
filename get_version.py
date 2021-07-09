"""
A version helper in the spirit of versioneer.
Minimalistic and able to run without build step using pkg_resources.
"""

# __version__ is defined at the very end of this file.

import re
import os
import typing as t
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from functools import partial
from pathlib import Path
from textwrap import indent
from typing import Union, Optional


RE_PEP440_VERSION = re.compile(
    r"""
(?:(?P<epoch>[0-9]+)!)?
(?P<base>[0-9]+(?:\.[0-9]+)*)
(?:
    [-_.]?
    (?P<stage>
        a|b|c|rc|alpha|beta|pre|preview  # pre-releases
        |post|rev|r
        |dev
    )
    [-_.]?
    (?P<revision>[0-9]+)?
)*
(?:-(?P<alt_post_revision>[0-9]+))?
(?:\+(?P<tagged_metadata>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?
""",
    re.VERBOSE,
)
RE_GIT_DESCRIBE = r"v?(?:([\d.]+)-(\d+)-g)?([0-9a-f]{7})(-dirty)?"
ON_RTD = os.environ.get("READTHEDOCS") == "True"


@contextmanager
def working_dir(dir_: Optional[os.PathLike] = None):
    curdir = os.getcwd()
    try:
        if dir_ is not None:
            os.chdir(dir_)
        yield
    finally:
        os.chdir(curdir)


class Source(Enum):
    dirname = "Directory name"
    vcs = "VCS"
    metadata = "Package metadata"


@dataclass
class NoVersionFound(RuntimeError):
    source: t.Optional[Source] = None
    msg: t.Optional[str] = None

    def __str__(self) -> str:
        src = f" via {self.source.value}" if self.source else ""
        if self.msg is not None:
            delim = "\n" if "\n" in self.msg else " "
            msg = f":{delim}{self.msg}"
        else:
            msg = "."
        return f"No version found{src}{msg}"


def get_version_from_dirname(parent: Path) -> Optional[str]:
    """Extracted sdist"""
    parent = parent.resolve()
    re_dirname = re.compile(
        f"[A-Za-z]+(?:[_-][A-Za-z]+)*-(?P<version>{RE_PEP440_VERSION.pattern})$",
        re.VERBOSE,
    )
    match = re_dirname.match(parent.name)
    if not match:
        raise NoVersionFound(
            Source.dirname,
            f"Name of directory “{parent}” does not contain a valid version.",
        )
    return match["version"]


def dunamai_get_from_vcs(dir_: Path):
    from dunamai import Version

    with working_dir(dir_):
        return Version.from_any_vcs(f"(?x)v?{RE_PEP440_VERSION.pattern}")


def get_version_from_vcs(parent: Path) -> Optional[str]:
    parent = parent.resolve()
    try:
        version = dunamai_get_from_vcs(parent)
    except (RuntimeError, ImportError) as e:
        raise NoVersionFound(
            Source.vcs,
            f"starting in directory {parent}, encountered: {e}",
        )
    return version.serialize(dirty=not ON_RTD)


def get_version_from_metadata(
    name: str, parent: Optional[Path] = None
) -> Optional[str]:
    try:
        from importlib.metadata import distribution, PackageNotFoundError
    except ImportError:
        from importlib_metadata import distribution, PackageNotFoundError

    try:
        pkg = distribution(name)
    except PackageNotFoundError:
        raise NoVersionFound(Source.metadata, f"could not find distribution {name}")

    # For an installed package, the parent is the install location
    pkg_paths = {
        Path(pkg.locate_file(mod)).parent.resolve()
        for mod in (pkg.read_text("top_level.txt") or "").split()
    }
    if parent is not None and parent.resolve() not in pkg_paths:
        msg = (
            "Distribution and package parent paths do not match;\n"
            f"{parent.resolve()}\nis not"
        )
        if len(pkg_paths) > 1:
            msg += " one of" + "".join(f"\n- {p}" for p in pkg_paths)
        else:
            msg += f"\n{next(iter(pkg_paths))}"
        raise NoVersionFound(Source.metadata, msg)

    return pkg.version


def get_version(package: Union[Path, str], *, dist_name: Optional[str] = None) -> str:
    """Get the version of a package or module

    Pass a module path or package name (``dist_name``).
    The former is recommended, since it also works for not yet installed packages.

    Supports getting the version from

    #. The directory name (as created by ``setup.py sdist``)
    #. The output of ``git describe``
    #. The package metadata of an installed package
       (This is the only possibility when passing a name)

    Args:
       package: package name or module path (``…/module.py`` or ``…/module/__init__.py``)
       dist_name: If the distribution name isn’t the same as the module name,
                  you can specify it, e.g. in ``PIL/__init__.py``,
                  there would be ``get_version(__file__, 'Pillow')``
    """
    path = Path(package)
    if dist_name is None and not path.suffix and len(path.parts) == 1:
        # Is probably not a path
        dist_name = path.name
        v = get_version_from_metadata(dist_name)
        if v:
            return str(v)

    if path.suffix != ".py":
        msg = f"“package” is neither the name of an installed module nor the path to a .py file."
        if path.suffix:
            msg += f" Unknown file suffix {path.suffix}"
        raise ValueError(msg)
    if path.name == "__init__.py":
        mod_name = path.parent.name
        parent = path.parent.parent
    else:
        mod_name = path.with_suffix("").name
        parent = path.parent
    if dist_name is None:
        dist_name = mod_name
    if parent.name == "src":
        parent = parent.parent

    errors = []
    for method in (
        get_version_from_dirname,
        get_version_from_vcs,
        partial(get_version_from_metadata, dist_name),
    ):
        try:
            version = method(parent)
        except NoVersionFound as e:
            errors.append(e)
        else:
            break
    else:
        msg = "\n".join(f"- {e.source.value}:{maybe_indent(e.msg)}" for e in errors)
        raise NoVersionFound(None, msg)

    assert RE_PEP440_VERSION.match(version)
    return version


def maybe_indent(msg: str) -> str:
    return f"\n{indent(msg, '  ')}" if "\n" in msg else f" {msg}"


__version__ = get_version(__file__)


if __name__ == "__main__":
    print(__version__)
