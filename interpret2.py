from ast import Str
from collections import deque
from operator import attrgetter, methodcaller
from types import CodeType, FrameType, FunctionType, NoneType
from typing import _Alias, Any, Callable, Deque, Generator, List, Mapping, Tuple
from inspect import getcallargs

from .structs import Frame, Function, Block
from .helpers import init_gens

# type for all *args/**kwds function arguments
_ArgsKwds = _Alias['_ArgsKwds', Tuple[Tuple, Mapping[Str, Any]]]


def cons_frame() -> Generator[FrameType, Tuple[Callable, _ArgsKwds], NoneType]:
    # get_func_attr = attrgetter("__name__", "__code__", "__defaults__", "__closure__")
    frame = None
    while True:
        func_obj, callargs = yield frame
        args, kwds = callargs
        callargs = getcallargs(func_obj, *args, **kwds)
        frame = Frame(frame.__code__, callargs)

def eval_frame(
    global_env: Mapping[Str, Any],
    call_stack: Deque[FrameType],
    block_stack: Deque[Block], 
    data_stack: Deque
) -> Generator:
    
    while True:
        frame = yield
        call_stack.append(frame)

def interpreter(global_env: Mapping[Str, Any]) -> Generator[Any]:
    CALL_STACK = deque()
    BLOCK_STACK = deque()
    DATA_STACK = deque()

    c_frame = cons_frame()

    init_gens(c_frame)

    while True:
        meaby_frame, args, kwds = yield
        if not isinstance(meaby_frame, FrameType):
            frame = c_frame.send(meaby_frame, *args, **kwds)






    