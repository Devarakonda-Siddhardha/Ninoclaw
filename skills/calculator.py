"""
Calculator skill — safe math expression evaluator
"""
import ast, math

SKILL_INFO = {
    "name": "calculator",
    "description": "Evaluate mathematical expressions including trig, logarithms, etc.",
    "version": "1.0",
    "icon": "🔢",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Evaluate a math expression. Supports +,-,*,/,**,sqrt,sin,cos,tan,log,pi,e",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression, e.g. sqrt(144) or 2**10"}
            },
            "required": ["expression"]
        }
    }
}]

_SAFE_NAMES = {
    "sqrt": math.sqrt, "abs": abs, "round": round,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "log": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp, "floor": math.floor, "ceil": math.ceil,
    "pi": math.pi, "e": math.e, "tau": math.tau,
    "factorial": math.factorial, "pow": pow,
}

_ALLOWED = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Num,
    ast.Add, ast.Sub, ast.Mul, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd, ast.Call, ast.Name, ast.Load,
)

def _safe_eval(expr):
    tree = ast.parse(expr.strip(), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise ValueError(f"Not allowed: {type(node).__name__}")
    return eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, _SAFE_NAMES)

def execute(tool_name, arguments):
    if tool_name != "calculate":
        return None
    expr = arguments.get("expression", "").strip()
    try:
        result = _safe_eval(expr)
        if isinstance(result, float) and result == int(result):
            result = int(result)
        elif isinstance(result, float):
            result = round(result, 10)
        return f"🔢 `{expr}` = **{result}**"
    except Exception as e:
        return f"❌ Cannot calculate `{expr}`: {e}"
