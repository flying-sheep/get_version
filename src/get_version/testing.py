from __future__ import annotations

from collections.abc import Callable, Generator, ItemsView, Iterator, Mapping
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Protocol, Union, runtime_checkable

import pytest

if TYPE_CHECKING:

    @runtime_checkable
    class Desc(Protocol):
        def __getitem__(self, key: DescK) -> DescV:
            ...

        def __iter__(self) -> Iterator[DescK]:
            ...

        def items(self) -> ItemsView[DescK, DescV]:
            ...

    DescK = Union[str, Path]
    DescV = Union[Desc, str, bytes]
    TempTreeCB = Callable[[Desc], Path]


@pytest.fixture(scope="function")
def temp_tree() -> Generator[Callable[[Desc], Path], None, None]:
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

    dirs: list[TemporaryDirectory] = []

    def get_temptree(desc: Desc) -> Path:
        d = TemporaryDirectory()
        mk_tree(desc, Path(d.name))
        dirs.append(d)
        return Path(d.name)

    yield get_temptree

    # Cleanup after the test function is through
    for d in dirs:
        d.cleanup()
