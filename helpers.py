from typing import Any, List, Generator
from types import CellType
from operator import methodcaller


def make_cell(value: Any) -> CellType:
    """Create a real Python closure and grab a cell."""
    fn = (lambda x: lambda: x)(value)
    return fn.__closure__[0]


def init_gens(*gens: List[Generator]) -> None:
    init = methodcaller("send", None)
    list(map(init, gens))
    return gens
