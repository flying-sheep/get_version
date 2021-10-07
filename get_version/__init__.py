"""
A version helper in the spirit of versioneer.
Minimalistic and able to run without build step using pkg_resources.
"""

# __version__ is defined at the very end of this file.

from __future__ import annotations

import re
import os
import typing as t
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from functools import partial
from pathlib import Path
from subprocess import run
from textwrap import indent

try:
    from typing import Literal
except ImportError:
    if t.TYPE_CHECKING:
        raise
    else:
        from typing_extensions import Literal

try:
    from importlib.metadata import distribution, Distribution, PackageNotFoundError
except ImportError:
    if t.TYPE_CHECKING:
        raise
    else:
        from importlib_metadata import distribution, Distribution, PackageNotFoundError


if t.TYPE_CHECKING:
    from dunamai import Version


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

VCS = Literal["any", "git", "mercurial"]  # "darcs", "subversion", "bazaar", "fossil"


@contextmanager
def working_dir(dir_: t.Optional[os.PathLike] = None):
    curdir = os.getcwd()
    try:
        if dir_ is not None:
            os.chdir(dir_)
        yield
    finally:
        os.chdir(curdir)


class Source(Enum):
    all: None = None
    dirname = "Directory name"
    vcs = "VCS"
    metadata = "Package metadata"

    def __bool__(self) -> bool:
        return self is not Source.all


@dataclass
class NoVersionFound(RuntimeError):
    source: Source
    msg: str

    def __str__(self) -> str:
        src = f" via {self.source.value}" if self.source else ""
        delim = "\n" if "\n" in self.msg else " "
        return f"No version found{src}:{delim}{self.msg}"


def get_version_from_dirname(parent: Path) -> str:
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
            f"name of directory “{parent}” does not contain a valid version.",
        )
    return match["version"]


def get_version_from_vcs(parent: Path, *, vcs: VCS = "any") -> str:
    parent = parent.resolve()
    vcs_root = find_vcs_root(parent, vcs=vcs)
    if vcs_root is None:
        raise NoVersionFound(
            Source.vcs, f"could not find VCS from directory “{parent}”."
        )
    if parent != vcs_root:
        raise NoVersionFound(
            Source.vcs, f"directory “{parent}” does not match VCS root “{vcs_root}”."
        )
    try:
        version = dunamai_get_from_vcs(parent)
    except (RuntimeError, ImportError, ValueError) as e:
        raise NoVersionFound(
            Source.vcs,
            f"starting in directory “{parent}”, encountered: {e}",
        )
    try:
        return version.serialize(dirty=not ON_RTD)
    except ValueError as e:
        raise NoVersionFound(
            Source.vcs,
            f"starting in directory “{parent}”, found unserializable version: {e}",
        )


def find_vcs_root(start: Path, *, vcs: VCS = "any") -> t.Optional[Path]:
    from dunamai import _detect_vcs, Vcs

    if vcs == "any":
        with working_dir(start):
            try:
                vcs_e = _detect_vcs()
            except RuntimeError:
                return None
    else:
        vcs_e = Vcs(vcs)

    if vcs_e is Vcs.Git:
        cmd = ["git", "rev-parse", "--show-toplevel"]
    elif vcs_e is Vcs.Mercurial:
        cmd = ["hg", "root"]
    else:
        raise NotImplementedError(
            f"Please file a feature request to implement support for {vcs_e.value}."
        )
    ret = run(cmd, cwd=start, capture_output=True)
    if ret.returncode != 0:
        return None  # Swallow stderr. Maybe we should logging.debug() it instead?
    return Path(os.fsdecode(ret.stdout.rstrip(b"\n")))


def dunamai_get_from_vcs(dir_: Path) -> Version:
    from dunamai import Version

    with working_dir(dir_):
        return Version.from_any_vcs(f"(?x)v?{RE_PEP440_VERSION.pattern}")


def get_version_from_metadata(name: str, parent: t.Optional[Path] = None) -> str:
    try:
        pkg = distribution(name)
    except PackageNotFoundError:
        raise NoVersionFound(Source.metadata, f"could not find distribution “{name}”.")

    # For an installed package, the parent is the install location,
    # For a dev package, it is the VCS repository.
    (install_path,) = {p.parent.resolve() for p in get_pkg_paths(pkg)}
    if parent is not None and parent.resolve() != install_path:
        msg = (
            "Distribution and package parent paths do not match;\n"
            f"{parent.resolve()}\nis not\n{install_path}"
        )
        raise NoVersionFound(Source.metadata, msg)

    return pkg.version


def get_pkg_paths(pkg: Distribution) -> t.List[Path]:
    # Some egg-info packages have e.g. src/ paths in their SOURCES.txt file,
    # but they also have this:
    mods = set((pkg.read_text("top_level.txt") or "").split())
    if not mods and pkg.files:
        # Fall back to RECORD file for dist-info packages without top_level.txt
        mods = {
            f.parts[0] if len(f.parts) > 1 else f.with_suffix("").name
            for f in pkg.files
            if f.suffix == ".py" or Path(pkg.locate_file(f)).is_symlink()
        }
    if not mods:
        raise RuntimeError(
            f"Can’t determine top level packages of {pkg.metadata['Name']}"
        )
    return [Path(pkg.locate_file(mod)) for mod in mods]


def get_version(
    package: t.Union[Path, str],
    *,
    dist_name: t.Optional[str] = None,
    vcs: VCS = "any",
) -> str:
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
       vcs: Pass one of the supported VCSs to skip (slow) VCS detection
    """
    path = Path(package)
    if dist_name is None and not path.suffix and len(path.parts) == 1:
        # Is probably not a path
        dist_name = path.name
        return get_version_from_metadata(dist_name)

    if path.suffix != ".py":
        msg = (
            f"“{package}” is neither the name of an installed module "
            "nor the path to a .py file."
        )
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

    methods: t.Iterable[t.Callable[[Path], str]] = (
        get_version_from_dirname,
        partial(get_version_from_vcs, vcs=vcs),
        partial(get_version_from_metadata, dist_name),
    )
    errors = []
    for method in methods:
        try:
            version = method(parent)
        except NoVersionFound as e:
            errors.append(e)
        else:
            break
    else:
        msg = "\n".join(f"- {e.source.value}:{maybe_indent(e.msg)}" for e in errors)
        raise NoVersionFound(Source.all, msg)

    assert RE_PEP440_VERSION.match(version)
    return version


def maybe_indent(msg: str) -> str:
    return f"\n{indent(msg, '  ')}" if "\n" in msg else f" {msg}"


__version__ = get_version(__file__)


if __name__ == "__main__":
    print(__version__)
