from ast import Str
from dataclasses import dataclass, field
from types import CellType, CodeType, FunctionType
from typing import Mapping, Any, Tuple

from .helpers import make_cell


@dataclass(slots=True)
class Frame:
    """Realistic frame class."""

    code: CodeType
    local_env: Mapping[Str, Any]
    # global_env: Mapping[Str, Any] = field(default={})


@dataclass(slots=True)
class Block:
    """Realistic code block."""

    type: Str
    handler: Any
    stack_height: int


@dataclass
class Function:
    """Realistic function class."""

    name: Str
    code: CodeType
    argdefs: Tuple[Any] = field(default=())
    closure: Tuple[CellType] = field(default=())

    def __post_init__(self) -> None:
        if self.closure:
            self.closure = tuple(map(make_cell, self.closure))
        # self.__dict__: Mapping[Str, Any] = {}
        self.__doc__: Str = self.code.co_consts[0] if self.code.co_consts else None

    def __call__(self, *args: Any, **kwds: Any) -> Any:

        return FunctionType(
            self.code,
            globals(),
            name=self.name,
            argdefs=self.argdefs,
            closure=self.closure,
        )(*args, **kwds)
