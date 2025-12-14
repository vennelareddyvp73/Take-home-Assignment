
import re
from typing import Dict, List, Tuple

VALID_FIELDS = {"open", "high", "low", "close", "volume"}

SHIFT_FUNC_PATTERN = re.compile(
    r"^[a-zA-Z_]+\s*\.\s*shift\(\s*\d+\s*\)$"
)

MINMAX_FUNC_PATTERN = re.compile(
    r"^(min|max)\(\s*[a-zA-Z_]+\s*,\s*\d+\s*\)$"
)

INDICATOR_PATTERN = re.compile(
    r"^(sma|ema|rsi|macd|bbands|atr|adx|stoch|pct_change)"
    r"\(\s*[a-zA-Z_][a-zA-Z0-9_]*(?:\s*,\s*\d+)*\s*\)$",
    re.IGNORECASE,
)

VALID_OPERATORS = {
    ">", "<", ">=", "<=", "==", "!=",
    "cross_above", "cross_below",
}

VALID_LOGICAL = {"AND", "OR"}


def is_number(x) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False


def is_indicator(expr: str) -> bool:
    return bool(INDICATOR_PATTERN.match(expr))


def is_shift(expr: str) -> bool:
    return bool(SHIFT_FUNC_PATTERN.match(expr))


def is_minmax(expr: str) -> bool:
    return bool(MINMAX_FUNC_PATTERN.match(expr))


def is_valid_operand(expr) -> bool:
    if expr in VALID_FIELDS:
        return True
    if is_number(expr):
        return True
    if isinstance(expr, str):
        return is_indicator(expr) or is_shift(expr) or is_minmax(expr)
    return False


def validate_condition(cond: dict) -> Tuple[bool, str]:
    left = cond.get("left")
    op = cond.get("operator")
    right = cond.get("right")

    if left is None or op is None or right is None:
        return False, "Missing left/operator/right"

    if not is_valid_operand(left):
        return False, f"Invalid left operand: {left}"

    if op not in VALID_OPERATORS:
        return False, f"Invalid operator: {op}"

    if not is_valid_operand(right):
        return False, f"Invalid right operand: {right}"

    return True, ""


def validate_parsed_json(parsed: dict) -> Tuple[bool, List[str]]:
    errors = []

    for block_name in ("entry", "exit"):
        block = parsed.get(block_name, {})
        conds = block.get("conditions", [])
        ops = block.get("operators", [])

        if len(ops) > max(0, len(conds) - 1):
            errors.append(f"[{block_name}] too many logical operators")

        for i, cond in enumerate(conds):
            ok, msg = validate_condition(cond)
            if not ok:
                errors.append(f"[{block_name} condition #{i}] {msg}")

        for op in ops:
            if op.upper() not in VALID_LOGICAL:
                errors.append(f"[{block_name}] invalid logical operator {op}")

    return (len(errors) == 0), errors


def cond_to_dsl(cond: dict) -> str:
    op = cond["operator"]
    if op == "cross_above":
        op = "CROSS_ABOVE"
    elif op == "cross_below":
        op = "CROSS_BELOW"

    return f"{cond['left']} {op} {cond['right']}"


def build_block(block: dict, indent: int = 1) -> str:
    pad = "    " * indent
    conds = block.get("conditions", [])
    ops = [o.upper() for o in block.get("operators", [])]

    if not conds:
        return f"{pad}(FALSE)"

    tokens = [cond_to_dsl(conds[0])]
    for i in range(1, len(conds)):
        tokens.append(ops[i - 1] if i - 1 < len(ops) else "AND")
        tokens.append(cond_to_dsl(conds[i]))

    return f"{pad}({' '.join(tokens)})"


def generate_dsl(parsed_json: dict) -> str:
    ok, errs = validate_parsed_json(parsed_json)
    if not ok:
        raise ValueError("Validation failed:\n" + "\n".join(errs))

    entry = build_block(parsed_json.get("entry", {}))
    exit_ = build_block(parsed_json.get("exit", {}))

    return f"""ENTRY:
{entry}

EXIT:
{exit_}
"""
