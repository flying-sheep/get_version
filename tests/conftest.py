from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, Callable, Dict, List

import pytest


Desc = Dict[Union[str, Path], Union["Desc", str, bytes]]


@pytest.fixture(scope="function")
def temp_tree() -> Callable[[Desc], Path]:
    def mk_tree(desc: Desc, parent: Path):
        parent.mkdir(parents=True, exist_ok=True)
        for name, content in desc.items():
            path = parent / name
            if isinstance(content, str):
                path.write_text(content)
            elif isinstance(content, bytes):
                path.write_bytes(content)
            else:
                assert isinstance(content, dict)
                mk_tree(content, path)

    dirs = []  # type: List[TemporaryDirectory]

    def get_temptree(desc: Desc) -> Path:
        d = TemporaryDirectory()
        mk_tree(desc, Path(d.name))
        dirs.append(d)
        return Path(d.name)

    yield get_temptree

    # Cleanup after the test function is through
    for d in dirs:
        d.cleanup()
