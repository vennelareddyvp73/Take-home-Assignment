import pandas as pd
import numpy as np
from pprint import pprint


def compute_sma(df, column, window):
    """Simple Moving Average"""
    return df[column].rolling(window).mean()


def compute_ema(df, column, window):
    """Exponential Moving Average"""
    return df[column].ewm(span=window, adjust=False).mean()


def compute_rsi(df, column, window):
    """Relative Strength Index"""
    delta = df[column].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_pct_change(df, column, window):
    """
    Percentage change compared to N periods ago
    Example: pct_change(volume, 5) returns (current - 5 days ago) / 5 days ago * 100
    """
    shifted = df[column].shift(window)
    pct = ((df[column] - shifted) / shifted) * 100
    return pct




def generate_expression(node, df, cache):
    """
    Recursively converts an AST node into a pandas Series or scalar
    FIXED: Now properly handles AND/OR logical operators in binary_op
    """
    node_type = node["type"]


    if node_type == "series":
        return df[node["value"]]


    if node_type == "number":
        return node["value"]


    if node_type == "shift":
        field = node["field"]
        periods = node["periods"]
        return df[field].shift(periods)


    if node_type == "min":
        field = node["field"]
        window = node["window"]
        return df[field].rolling(window).min()


    if node_type == "max":
        field = node["field"]
        window = node["window"]
        return df[field].rolling(window).max()

    if node_type == "indicator":
        name = node["name"]
        source = node["params"][0]
        window = int(node["params"][1])

        key = f"{name}_{source}_{window}"

        if key not in cache:
            if name == "sma":
                cache[key] = compute_sma(df, source, window)
            elif name == "ema":
                cache[key] = compute_ema(df, source, window)
            elif name == "rsi":
                cache[key] = compute_rsi(df, source, window)
            elif name == "pct_change":
                cache[key] = compute_pct_change(df, source, window)
            else:
                raise ValueError(f"Unsupported indicator: {name}")

        return cache[key]


    if node_type == "binary_op":
        left = generate_expression(node["left"], df, cache)
        right = generate_expression(node["right"], df, cache)
        op = node["op"].lower()  # Normalize to lowercase

        
        if op == "and":
            return left & right
        if op == "or":
            return left | right

        # Comparison operators
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right

        # Crossing operators
        if op == "cross_above":
            left_prev = left.shift(1) if isinstance(left, pd.Series) else left
            right_prev = right.shift(1) if isinstance(right, pd.Series) else right
            prev_below = (left_prev <= right_prev)
            now_above = (left > right)
            return prev_below & now_above

        if op == "cross_below":
            left_prev = left.shift(1) if isinstance(left, pd.Series) else left
            right_prev = right.shift(1) if isinstance(right, pd.Series) else right
            prev_above = (left_prev >= right_prev)
            now_below = (left < right)
            return prev_above & now_below

        raise ValueError(f"Unsupported operator: {op}")

    raise ValueError(f"Unknown AST node type: {node_type}")



def generate_strategy(ast):
    """
    Takes an AST and returns a function that evaluates
    entry and exit signals over a DataFrame.
    
    """

    def strategy(df):
        cache = {}
        signals = pd.DataFrame(index=df.index)

        # ENTRY CONDITIONS
        entry_nodes = ast.get("entry", [])
        if entry_nodes:
            # If there's only one node and it's a binary_op tree, evaluate it directly
            if len(entry_nodes) == 1:
                signals["entry"] = generate_expression(entry_nodes[0], df, cache)
            else:
                # Multiple separate conditions - combine with AND
                entry_conditions = []
                for cond in entry_nodes:
                    entry_conditions.append(
                        generate_expression(cond, df, cache)
                    )
                signals["entry"] = np.logical_and.reduce(entry_conditions)
        else:
            signals["entry"] = False

        # EXIT CONDITIONS
        exit_nodes = ast.get("exit", [])
        if exit_nodes:
            # If there's only one node and it's a binary_op tree, evaluate it directly
            if len(exit_nodes) == 1:
                signals["exit"] = generate_expression(exit_nodes[0], df, cache)
            else:
                # Multiple separate conditions - combine with OR
                exit_conditions = []
                for cond in exit_nodes:
                    exit_conditions.append(
                        generate_expression(cond, df, cache)
                    )
                signals["exit"] = np.logical_or.reduce(exit_conditions)
        else:
            signals["exit"] = False

        return signals

    return strategy