import enum
import typing as t

class Style(enum.Enum):
    Pep440 = enum.auto()
    SemVer = enum.auto()
    Pvp = enum.auto()

class Vcs(enum.Enum):
    Any = enum.auto()
    Git = enum.auto()
    Mercurial = enum.auto()
    # and more

def _detect_vcs() -> Vcs: ...

class Version:
    def __init__(
        self,
        base: str,
        *,
        stage: t.Tuple[str, t.Optional[int]] = None,
        distance: int = 0,
        commit: str = None,
        dirty: bool = None,
        tagged_metadata: t.Optional[str] = None,
    ) -> None: ...
    @staticmethod
    def from_any_vcs(
        pattern: str = "...",
        latest_tag: bool = False,
        tag_dir: str = "tags",
    ) -> Version: ...
    def serialize(
        self,
        metadata: bool = None,
        dirty: bool = False,
        format: str = None,
        style: Style = None,
        bump: bool = False,
        tagged_metadata: bool = False,
    ) -> str: ...
