"""Calculator tool — safe arithmetic via AST (no eval)."""

import ast
import operator
from typing import Any

from worker.tools.base import Tool, ToolExecutionError

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ToolExecutionError("Only numeric literals are allowed.")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        if isinstance(node.op, ast.Pow):
            right = _eval(node.right)
            if right > 100:
                raise ToolExecutionError("Exponent too large.")
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ToolExecutionError("Unsupported expression.")


def safe_eval(expression: str) -> float:
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolExecutionError(f"Invalid expression: {exc.msg}") from exc
    return _eval(parsed)


class CalculatorTool(Tool):
    name = "calculator"
    description = "Evaluate a basic arithmetic expression (+, -, *, /, %, **)."
    input_schema = {"expression": "string"}
    output_schema = {"expression": "string", "result": "number"}

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # Default expression keeps the demo path working when none is provided.
        expression = str(input_data.get("expression") or "").strip() or "1 + 1"
        try:
            result = safe_eval(expression)
        except ToolExecutionError:
            raise
        except Exception as exc:  # e.g. ZeroDivisionError
            raise ToolExecutionError(f"calculation error: {exc}") from exc
        return {"expression": expression, "result": result}
