from lark import Lark, Transformer, exceptions
from pprint import pprint

dsl_grammar = r"""
    start: entry? exit?

    entry: "ENTRY:" expr
    exit:  "EXIT:" expr

    ?expr: expr LOGIC expr
         | "(" expr ")"
         | condition
         | FALSE

    condition: operand OP operand

    operand: shift_func
           | function_call
           | series
           | NUMBER

    series: NAME

    // Shift function: field.shift(N)
    shift_func: NAME "." "shift" "(" NUMBER ")"
    
    // Generic function call: name(field,N)
    // We'll detect min/max/sma/ema/rsi in transformer
    function_call: NAME "(" NAME "," NUMBER ")"

    LOGIC: "AND" | "OR"
    OP: ">=" | "<=" | ">" | "<" | "==" | "!="
        | "CROSS_ABOVE" | "CROSS_BELOW"
        | "cross_above" | "cross_below"
        | "rise_above" | "drop_below"

    NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
    NUMBER: /\d+(\.\d+)?/
    FALSE: "FALSE"

    %ignore " "
    %ignore /\n+/
"""


class DSLASTBuilder(Transformer):
    def start(self, items):
        ast = {"entry": [], "exit": []}
        for block in items:
            if "entry" in block:
                ast["entry"] = block["entry"]
            if "exit" in block:
                ast["exit"] = block["exit"]
        return ast

    def entry(self, items):
        return {"entry": [items[0]] if items[0] != "FALSE" else []}

    def exit(self, items):
        return {"exit": [items[0]] if items[0] != "FALSE" else []}

    def expr(self, items):
        if len(items) == 3:
            return {
                "type": "binary_op",
                "left": items[0],
                "op": items[1],
                "right": items[2]
            }
        return items[0]

    def condition(self, items):
        return {
            "type": "binary_op",
            "left": items[0],
            "op": items[1],
            "right": items[2]
        }

    def series(self, items):
        return {"type": "series", "value": items[0]}
    
    def shift_func(self, items):
        # e.g., high.shift(1)
        return {"type": "shift", "field": items[0], "periods": int(items[1])}
    
    def function_call(self, items):
        # e.g., sma(close,20) or max(high,5) or min(low,10)
        func_name = items[0].lower()
        field = items[1]
        param = items[2]
        
        # Detect if it's min/max vs indicator
        if func_name in ["min", "max"]:
            return {"type": func_name, "field": field, "window": int(param)}
        else:
            # It's an indicator (sma, ema, rsi, etc.)
            return {"type": "indicator", "name": func_name, "params": [field, param]}

    def operand(self, items):
        v = items[0]
        if isinstance(v, dict):
            return v
        return {"type": "number", "value": float(v)}

    def LOGIC(self, token):
        return str(token)

    def OP(self, token):
        return str(token).lower()

    def NAME(self, token):
        return str(token)

    def NUMBER(self, token):
        return float(token)

    def FALSE(self, token):
        return "FALSE"


parser = Lark(dsl_grammar, parser="lalr", transformer=DSLASTBuilder())

def parse_dsl(dsl_text):
    try:
        return parser.parse(dsl_text)
    except exceptions.UnexpectedInput as e:
        raise SyntaxError(
            f"DSL Syntax Error at line {e.line}, column {e.column}\n"
            f"{e.get_context(dsl_text)}"
        ) from None


