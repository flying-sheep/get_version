"""
A version helper in the spirit of versioneer.
Minimalistic and able to run without build step using pkg_resources.
"""

# __version__ is defined at the very end of this file.

import re
import os
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent
from typing import Union, Optional
from logging import getLogger


RE_PEP440_VERSION = re.compile(
    r"""
v?
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

logger = getLogger(__name__)


@contextmanager
def working_dir(dir_: Optional[os.PathLike] = None):
    curdir = os.getcwd()
    try:
        if dir_ is not None:
            os.chdir(dir_)
        yield
    finally:
        os.chdir(curdir)


def get_version_from_dirname(name: str, parent: Path) -> Optional[str]:
    """Extracted sdist"""
    parent = parent.resolve()
    logger.info(f"dirname: Trying to get version of {name} from dirname {parent}")

    name_re = name.replace("_", "[_-]")
    re_dirname = re.compile(f"{name_re}-{RE_PEP440_VERSION.pattern}$", re.VERBOSE)
    if not re_dirname.match(parent.name):
        logger.info(
            f"dirname: Failed; Directory name {parent.name!r} does not contain a valid version"
        )
        return None

    logger.info("dirname: Succeeded")
    return parent.name[len(name) + 1 :]


def dunamai_get_from_vcs(dir_: Path):
    from dunamai import Version

    with working_dir(dir_):
        return Version.from_any_vcs(f"(?x){RE_PEP440_VERSION.pattern}")


def get_version_from_vcs(parent: Path) -> Optional[str]:
    parent = parent.resolve()
    logger.info(f"git: Trying to get version from VCS in directory {parent}")

    try:
        version = dunamai_get_from_vcs(parent)
    except (RuntimeError, ImportError) as e:
        logger.info(f"dirname: Failed; {e}")
        return None

    logger.info("VCS: Succeeded")
    return version.serialize(dirty=not ON_RTD)


def get_version_from_metadata(
    name: str, parent: Optional[Path] = None
) -> Optional[str]:
    logger.info(f"metadata: Trying to get version for {name} in dir {parent}")
    try:
        from pkg_resources import get_distribution, DistributionNotFound
    except ImportError:
        logger.info("metadata: Failed; could not import pkg_resources")
        return None

    try:
        pkg = get_distribution(name)
    except DistributionNotFound:
        logger.info(f"metadata: Failed; could not find distribution {name}")
        return None

    # For an installed package, the parent is the install location
    path_pkg = Path(pkg.location).resolve()
    if parent is not None and path_pkg != parent.resolve():
        msg = f"""\
            metadata: Failed; distribution and package paths do not match:
            {path_pkg}
            !=
            {parent.resolve()}\
            """
        logger.info(dedent(msg))
        return None

    logger.info(f"metadata: Succeeded")
    return pkg.version


def get_version(package: Union[Path, str]) -> str:
    """Get the version of a package or module

    Pass a module path or package name.
    The former is recommended, since it also works for not yet installed packages.

    Supports getting the version from

    #. The directory name (as created by ``setup.py sdist``)
    #. The output of ``git describe``
    #. The package metadata of an installed package
       (This is the only possibility when passing a name)

    Args:
       package: package name or module path (``…/module.py`` or ``…/module/__init__.py``)
    """
    path = Path(package)
    if not path.suffix and len(path.parts) == 1:  # Is probably not a path
        v = get_version_from_metadata(package)
        if v:
            return str(v)

    if path.suffix != ".py":
        msg = f"“package” is neither the name of an installed module nor the path to a .py file."
        if path.suffix:
            msg += f" Unknown file suffix {path.suffix}"
        raise ValueError(msg)
    if path.name == "__init__.py":
        name = path.parent.name
        parent = path.parent.parent
    else:
        name = path.with_suffix("").name
        parent = path.parent
    if parent.name == "src":
        parent = parent.parent

    version = (
        get_version_from_dirname(name, parent)
        or get_version_from_vcs(parent)
        or get_version_from_metadata(name, parent)
    )

    if version is None:
        raise RuntimeError("No version found.")

    assert RE_PEP440_VERSION.match(version)
    return version


__version__ = get_version(__file__)


if __name__ == "__main__":
    print(__version__)
