import enum
import typing as t

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
    ): ...

    @staticmethod
    def from_any_vcs(
        pattern: str = '...',
        latest_tag: bool = False,
        tag_dir: str = 'tags',
    ): ...

class Vcs(enum.Enum):
    Any = enum.auto()
    Git = enum.auto()
    Mercurial = enum.auto()
    # and more
