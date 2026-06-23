import ast
import concurrent.futures
import io
import math

import pandas as pd

BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "socket", "requests", "urllib",
    "shutil", "pathlib", "glob", "tempfile", "pickle",
}

BLOCKED_BUILTINS = {
    "open", "eval", "exec", "__import__", "compile",
    "breakpoint", "input",
}


def validate_code(code: str) -> tuple[bool, str]:
    """AST pass: block dangerous imports and builtins. Returns (is_safe, reason).

    Walk the AST and reject any Import/ImportFrom node whose module root is in
    BLOCKED_IMPORTS, or any Call node whose function name is in BLOCKED_BUILTINS.

    Returns (True, "") when code is safe to run.
    Returns (False, "<reason>") when a blocked pattern is found.
    """
    # TODO: parse `code` with ast.parse and walk the tree
    # TODO: for each ast.Import/ast.ImportFrom node, check the module root against BLOCKED_IMPORTS
    # TODO: for each ast.Call node, check the function name against BLOCKED_BUILTINS
    # TODO: return (False, "blocked import: <name>") or (False, "blocked call: <name>") if found
    # TODO: return (True, "") if nothing is blocked
    raise NotImplementedError


def run_sandboxed(
    code: str,
    dataframes: dict[str, pd.DataFrame],
    timeout: int = 30,
) -> tuple[str, str]:
    """Execute code in restricted globals with timeout.

    Returns (stdout, error). DataFrames are injected directly — no imports needed.
    __builtins__ is empty so open/eval/exec are unavailable at runtime.

    Build a safe_globals dict with:
      - "__builtins__": {}          — removes access to all builtins
      - "pd": pd                    — pandas is available
      - "math": math                — math module is available
      - "print": <write to buf>     — print() writes to a StringIO buffer
      - **dataframes                — DataFrames are injected by name

    Execute code in a ThreadPoolExecutor with the given timeout.
    If execution exceeds timeout, return ("", "execution timed out").
    If execution raises an exception, return ("", str(exc)).
    """
    # TODO: create a StringIO buffer (buf) to capture print() output
    # TODO: build safe_globals with __builtins__={}, pd, math, a print replacement, and dataframes
    # TODO: define a _exec() function that calls exec(code, safe_globals)
    # TODO: run _exec() in a ThreadPoolExecutor with the timeout
    # TODO: return (buf.getvalue().strip(), "") on success
    # TODO: return ("", "execution timed out") on TimeoutError
    # TODO: return ("", str(exc)) on any other exception
    raise NotImplementedError
