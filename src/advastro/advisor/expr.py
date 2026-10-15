"""Safe evaluation of the small expressions used in rule files.

Allowed: names (facts), numbers, strings, lists, comparisons, and/or/not,
arithmetic, `x if c else y`, `in`, and a few functions (min, max, abs, round,
len). Anything else is rejected, so rule files can never run arbitrary code.
A comparison involving an unknown fact (None) is simply false.
"""

from __future__ import annotations

import ast
import operator

_FUNCS = {"min": min, "max": max, "abs": abs, "round": round, "len": len}
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
_CMP = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
        ast.Eq: operator.eq, ast.NotEq: operator.ne,
        ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}


class ExpressionError(ValueError):
    pass


class _Unknown:
    """Result of an operation on missing data; falsy, and comparisons are false."""

    def __bool__(self) -> bool:
        return False


UNKNOWN = _Unknown()


def evaluate(expression: str, facts: dict):
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"Invalid expression: {expression!r}") from exc
    return _eval(tree.body, facts)


def _eval(node, facts):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in ("True", "False", "None"):
            return {"True": True, "False": False, "None": None}[node.id]
        value = facts.get(node.id)
        return UNKNOWN if value is None else value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e, facts) for e in node.elts]
    if isinstance(node, ast.BoolOp):
        values = (_eval(v, facts) for v in node.values)
        if isinstance(node.op, ast.And):
            result = True
            for v in values:
                result = v
                if not v:
                    return v
            return result
        result = False
        for v in values:
            result = v
            if v:
                return v
        return result
    if isinstance(node, ast.UnaryOp):
        value = _eval(node.operand, facts)
        if isinstance(node.op, ast.Not):
            return not value
        if isinstance(node.op, ast.USub):
            return UNKNOWN if value is UNKNOWN else -value
        raise ExpressionError("Unsupported operator")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        a, b = _eval(node.left, facts), _eval(node.right, facts)
        if a is UNKNOWN or b is UNKNOWN:
            return UNKNOWN
        try:
            return _BIN[type(node.op)](a, b)
        except (TypeError, ZeroDivisionError):
            return UNKNOWN
    if isinstance(node, ast.Compare):
        left = _eval(node.left, facts)
        for op, comp in zip(node.ops, node.comparators, strict=True):
            right = _eval(comp, facts)
            if left is UNKNOWN or right is UNKNOWN or type(op) not in _CMP:
                return False
            try:
                if not _CMP[type(op)](left, right):
                    return False
            except TypeError:
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        return _eval(node.body, facts) if _eval(node.test, facts) else _eval(node.orelse, facts)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in _FUNCS and not node.keywords:
        args = [_eval(a, facts) for a in node.args]
        if any(a is UNKNOWN for a in args):
            return UNKNOWN
        try:
            return _FUNCS[node.func.id](*args)
        except (TypeError, ValueError):
            return UNKNOWN
    raise ExpressionError(f"Not allowed in rules: {ast.dump(node)[:60]}")
