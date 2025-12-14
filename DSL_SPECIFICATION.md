# DSL Specification Document

## Overview

This document describes the Domain-Specific Language (DSL) for expressing algorithmic trading strategies. The DSL provides a clear syntax for defining entry and exit conditions using technical indicators, price comparisons, and boolean logic.

## Grammar Structure

### Basic Syntax

```
ENTRY:
    <condition>

EXIT:
    <condition>
```

Both `ENTRY` and `EXIT` blocks are optional. Use `(FALSE)` when no condition is needed.

### Elements

#### 1. Comparison Operators

| Operator      | Meaning                  |
|-------------- |--------------------------|
| `>`           | Greater than             |
| `<`           | Less than                |
| `>=`          | Greater than or equal to |
| `<=`          | Less than or equal to    |
| `==`          | Equal to                 |
| `!=`          | Not equal to             |
| `cross_above` | Price crosses above      |
| `cross_below` | Price crosses below      |

#### 2. Logical Operators

| Operator | Meaning                       |
|----------|-------------------------------|
| `AND`    | Both conditions must be true  |
| `OR`     | Either condition must be true |

#### 3. Series (Fields)

Valid field names from OHLCV data:
- `open` - Opening price
- `high` - Highest price
- `low` - Lowest price
- `close` - Closing price
- `volume` - Trading volume

#### 4. Functions

**Indicators**
- `sma(field, N)` - Simple Moving Average over N periods
- `ema(field, N)` - Exponential Moving Average over N periods
- `rsi(field, N)` - Relative Strength Index over N periods
- `pct_change(field, N)` - Percentage change compared to N periods ago

**Time Functions**
- `field.shift(N)` - Value from N periods ago
- `max(field, N)` - Maximum value over N periods
- `min(field, N)` - Minimum value over N periods

#### 5. Numbers

Integer or decimal literals (e.g., `100`, `1000000`, `30.5`)

## Complete Examples

### Example 1: Moving Average with Volume Filter

**Natural Language:**
```
Buy when the close price is above the 20-day moving average and volume is above 1 million.
```

**DSL:**
```
ENTRY:
    (close > sma(close,20) AND volume > 1000000)
EXIT:
    (FALSE)
```

**Generated AST:**
```python
{
  'entry': [
    {
      'left': {
        'left': {'type': 'series', 'value': 'close'},
        'op': '>',
        'right': {'name': 'sma', 'params': ['close', 20.0], 'type': 'indicator'},
        'type': 'binary_op'
      },
      'op': 'AND',
      'right': {
        'left': {'type': 'series', 'value': 'volume'},
        'op': '>',
        'right': {'type': 'number', 'value': 1000000.0},
        'type': 'binary_op'
      },
      'type': 'binary_op'
    }
  ],
  'exit': []
}
```

**Explanation:**
- Entry requires TWO conditions (connected by AND)
- Condition 1: Close price must be above 20-period SMA
- Condition 2: Volume must exceed 1,000,000
- No exit condition specified

---

### Example 2: Yesterday's High Breakout

**Natural Language:**
```
Enter when price crosses above yesterday's high.
```

**DSL:**
```
ENTRY:
    (close cross_above high.shift(1))
EXIT:
    (FALSE)
```

**Generated AST:**
```python
{
  'entry': [
    {
      'left': {'type': 'series', 'value': 'close'},
      'op': 'cross_above',
      'right': {'field': 'high', 'periods': 1, 'type': 'shift'},
      'type': 'binary_op'
    }
  ],
  'exit': []
}
```

**Explanation:**
- Uses `cross_above` operator for breakout detection
- `high.shift(1)` references yesterday's high value
- Entry triggers when close crosses above (not just exceeds) yesterday's high

---

### Example 3: RSI Oversold Exit

**Natural Language:**
```
Exit when RSI(14) is below 30.
```

**DSL:**
```
ENTRY:
    (FALSE)
EXIT:
    (rsi(close,14) < 30)
```

**Generated AST:**
```python
{
  'entry': [],
  'exit': [
    {
      'left': {'name': 'rsi', 'params': ['close', 14.0], 'type': 'indicator'},
      'op': '<',
      'right': {'type': 'number', 'value': 30.0},
      'type': 'binary_op'
    }
  ]
}
```

**Explanation:**
- No entry condition (only exit defined)
- Uses RSI indicator with 14-period window
- Exit triggers when RSI falls below 30 (oversold condition)

---

### Example 4: Volume Spike Detection

**Natural Language:**
```
Trigger entry when volume increases by more than 30 percent compared to last week.
```

**DSL:**
```
ENTRY:
    (pct_change(volume,5) > 30)
EXIT:
    (FALSE)
```

**Generated AST:**
```python
{
  'entry': [
    {
      'left': {'name': 'pct_change', 'params': ['volume', 5.0], 'type': 'indicator'},
      'op': '>',
      'right': {'type': 'number', 'value': 30.0},
      'type': 'binary_op'
    }
  ],
  'exit': []
}
```

**Explanation:**
- Uses `pct_change` function to calculate percentage change
- Window of 5 periods (1 trading week)
- Entry when volume increases more than 30% compared to 5 days ago

---

## AST Node Types

The DSL parser generates an Abstract Syntax Tree with the following node types:

### binary_op
Represents an operation between two operands.
```python
{
  'type': 'binary_op',
  'left': <node>,
  'op': '<operator>',
  'right': <node>
}
```

### series
Represents a data field (close, volume, etc.).
```python
{
  'type': 'series',
  'value': 'close'
}
```

### number
Represents a numeric literal.
```python
{
  'type': 'number',
  'value': 100.0
}
```

### indicator
Represents a technical indicator function.
```python
{
  'type': 'indicator',
  'name': 'sma',
  'params': ['close', 20.0]
}
```

### shift
Represents a time-shifted value.
```python
{
  'type': 'shift',
  'field': 'high',
  'periods': 1
}
```

### min/max
Represents rolling minimum or maximum.
```python
{
  'type': 'max',
  'field': 'high',
  'window': 10
}
```

## Validation Rules

### Field Names
- Must be one of: `open`, `high`, `low`, `close`, `volume`
- Case-sensitive (lowercase only)

### Operators
- Comparison: `>`, `<`, `>=`, `<=`, `==`, `!=`, `cross_above`, `cross_below`
- Logical: `AND`, `OR`

### Function Calls
- Must use valid function names: `sma`, `ema`, `rsi`, `pct_change`, `min`, `max`
- First parameter: field name
- Second parameter: positive integer (window size)

### Numbers
- Can be integers or decimals
- No special notation required


## Summary

This DSL provides a clean, unambiguous language for expressing trading strategies. It successfully balances simplicity, power, and extensibility while maintaining formal grammar specification compatible with standard parsing tools.