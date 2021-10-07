from __future__ import annotations

import typing as t
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


if t.TYPE_CHECKING:

    @t.runtime_checkable
    class Desc(t.Protocol):
        def __getitem__(self, key: DescK) -> DescV:
            ...

        def __iter__(self) -> t.Iterator[DescK]:
            ...

        def items(self) -> t.ItemsView[DescK, DescV]:
            ...

    DescK = t.Union[str, Path]
    DescV = t.Union[Desc, str, bytes]
    TempTreeCB = t.Callable[[Desc], Path]


@pytest.fixture(scope="function")
def temp_tree() -> t.Generator[t.Callable[[Desc], Path], None, None]:
    def mk_tree(desc: Desc, parent: Path):
        parent.mkdir(parents=True, exist_ok=True)
        for name, content in desc.items():
            path = parent / name
            if isinstance(content, str):
                path.write_text(content)
            elif isinstance(content, bytes):
                path.write_bytes(content)
            else:
                assert isinstance(content, Mapping)
                mk_tree(content, path)

    dirs: t.List[TemporaryDirectory] = []

    def get_temptree(desc: Desc) -> Path:
        d = TemporaryDirectory()
        mk_tree(desc, Path(d.name))
        dirs.append(d)
        return Path(d.name)

    yield get_temptree

    # Cleanup after the test function is through
    for d in dirs:
        d.cleanup()
