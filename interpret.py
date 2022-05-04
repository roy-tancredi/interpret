from ast import Return
from collections import namedtuple
import dis
import inspect
import sys
from types import CellType, CodeType, FrameType, FunctionType, NoneType
from typing import Any, List, Mapping, Tuple
from dataclasses import dataclass, field


class VirtualMachineError(Exception):
    ...


@dataclass(slots=True)
class Frame:
    """Realistic frame."""

    code: CodeType
    global_env: Mapping
    local_env: Mapping
    prev_frame: FrameType
    data_stack: List[Any] = field(default_factory=list, init=False)
    block_stack: List[Any] = field(default_factory=list, init=False)
    pos = 0

    def __post_init__(self):
        if self.prev_frame:
            self.builtin_names = self.prev_frame.builtin_names
        else:
            self.builtin_names = self.local_names["__builtins__"]
            if hasattr(self.builtin_names, "__dict__"):
                self.builtin_names = self.builtin_names.__dict__


@dataclass
class Block:
    """Realistic code block."""

    type: str
    handler: Any
    stack_height: int


class VirtualMachine:
    """Simplified interpreter."""

    def __init__(self) -> None:
        self.call_stack: List[FrameType] = []
        self.frame: FrameType | NoneType  # current
        self.return_value: Any
        self.exception: Exception

    def construct_frame(
        self,
        code: CodeType,
        call_args: Mapping = {},
        global_env: Mapping | NoneType = None,
        local_env: Mapping | NoneType = None,
    ) -> FrameType:
        """Construct frame from prodecure and its context."""
        if global_env is not None and local_env is not None:
            local_env = global_env
        elif self.call_stack:
            global_env = self.frame.global_env
            local_env = {}
        else:
            global_env = local_env = {
                "__builtins__": __builtins__,
                "__name__": "__main__",
                "__doc__": None,
                "__package__": None,
            }
            local_env.update(call_args)
        return Frame(code, global_env, local_env, self.frame)

    # Call-stack manipulation

    def push_frame(self, frame: FrameType) -> None:
        """Push frame on the call stack."""
        self.call_stack.append(frame)
        self.frame = frame

    def pop_frame(self) -> None:
        """Pop frame from the call stack."""
        self.call_stack.pop()
        self.frame = self.call_stack[-1] if self.call_stack else None

    def run_frame(self, frame: FrameType) -> Return:
        """Evaluate a frame and return its value."""
        self.push_frame(frame)

        while True:
            op_name, argument = self.parse_instr_and_args(frame)
            output = self.dispatch(op_name, argument)
            while output and frame.block_stack:
                output = self.manage_block_stack(output)
            if output:
                break

        self.pop_frame()

        if output == "EXCEPTION":
            exc, val, tb = self.exception
            e = exc(val)
            e.__traceback__ = tb
            raise e

        return self.return_value

    # Block-stack manipulation

    def push_block(self, block_type: str, handler=None) -> None:
        """Push block on current frame's block stack."""
        stack_height = len(self.frame.data_stack)
        self.frame.block_stack.append(Block(block_type, handler, stack_height))

    def pop_block(self) -> Block:
        """Pop the top block from current frame's block stack."""
        return self.frame.block_stack.pop()

    def unwind_block(self, block: Block):
        ...

    # Data-stack manipulation

    def top(self) -> FrameType:
        """Get top value from current frame's data stack."""
        return self.frame.data_stack[-1]

    def pop(self) -> FrameType:
        """Pop the top value from current frame's data stack."""
        return self.frame.data_stack.pop()

    def push(self, *vals: List[Any]) -> None:
        """Push values on current frame's data stack."""
        self.frame.data_stack.extend(vals)

    def popn(self, n: int = 1) -> List[Any]:
        """Pop 'n' numbers od values from current frame's data stack."""
        top_n = self.frame.data_stack[-n:]
        self.frame.data_stack[-n:] = []
        return top_n

    def parse_instr_and_args(self, frame: FrameType) -> Tuple:
        """Specify the operation name and value of arguments."""
        op_bytes = frame.code.co_code[frame.pos]
        frame.pos += 1
        op_name = dis.opname[op_bytes]
        if op_bytes >= dis.HAVE_ARGUMENT:
            arg = frame.code.co_code[frame.pos : frame.pos + 2]
            frame.pos += 2
            arg_val = arg[0] + arg[1] * 256
            if op_bytes in dis.hasconst:
                arg = frame.code.co_consts[arg_val]
            elif op_bytes in dis.hasname:
                arg = frame.code.co_names[arg_val]
            elif op_bytes in dis.haslocal:
                arg = frame.code.co_varnames[arg_val]
            elif op_bytes in dis.hasjrel:
                arg = frame.pos + arg_val
            else:
                arg = arg_val
            argument = [arg]
        else:
            argument = []

        return op_name, argument

    def execute(
        self,
        code: CodeType,
        global_env: Mapping | NoneType = None,
        local_env: Mapping | NoneType = None,
    ) -> None:
        """..."""
        frame = self.construct_frame(code, global_env=global_env, local_env=local_env)

        ###################
        #   DISPATCHER    #
        ###################

    def dispatch(self, op_name: str, argument: Any) -> Any:
        """Dispatch operation 'op_name' with argument to a proper method."""
        output = None

        try:
            op_method = getattr(self, f"op_{op_name}", None)
            if not op_method:
                op_class = op_name.split("_")[1]
                if op_name.startswith("UNARY_"):
                    self.UNARY_OP(op_class)
                elif op_name.startswith("BINARY_"):
                    self.BINARY_OP(op_class)
                else:
                    raise NotImplementedError(f"Unsupported bytecode type: {op_name}.")
            else:
                output = op_method(*argument)
        except:
            self.exception = sys.exc_info()[:2] + (None,)
            output = "EXCEPTION"
        return output


class Function:
    """Realistic function class."""

    def __init__(
        self,
        name: str,
        code: CodeType,
        global_env: Mapping,
        defaults: Mapping,
        closure,
        vm: VirtualMachine,
    ) -> None:
        self._vm = vm
        self.name = self.__name__ = name or code.co_name
        self.code = code
        self.defaults = defaults
        self.global_env = global_env
        self.local_env = self._vm.frame.local_env
        self.closure = closure
        self.__dict__ = {}
        self.__doc__ = code.co_consts[0] if code.co_consts else None

        _kv = {
            "argdefs": self.defaults,
        }
        if closure:
            _kv["closure"] = tuple(self._make_cell(0) for _ in closure)
        self._func = FunctionType(code, global_env, **_kv)

    @staticmethod
    def _make_cell(value: Any) -> CellType:
        """Create a real Python closure and grab a cell."""
        fn = (lambda x: lambda: x)(value)
        return fn.__closure__[0]

    def __call__(self, *args: Any, **kwds: Any) -> FrameType:
        """Construct frame of self."""
        callargs = inspect.getcallargs(self._func, *args, **kwds)
        frame = self._vm.construct_frame(self.code, callargs, self.global_env, {})
        return self._vm.execute(frame)


class TestModel:
    a = "class attribute a"
    b = "class attribute b"

    def __init__(self):
        self.c = "instance attribute c"
        self.counter = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.counter >= 10:
            raise StopIteration
        self.counter += 1
        return self


Model = TestModel()
gen = ((model.a, len(model.c)) for model in Model if model.b not in ("a", "b", "c"))

l = lambda x: x


# (to_upper(user) for user in join(RadUser, RadLogAuth, on='user_id') if user.id == 200)
# SELECT UPPER(RadUser.user_id), * FROM TABLE RadUser WHERE RadUser.user_id = 200
