import re
import json

# ---------------------------------
# Keywords
# ---------------------------------
ENTRY_KEYWORDS = ["buy", "enter", "trigger entry"]
EXIT_KEYWORDS = ["sell", "exit", "close position"]

VALID_FIELDS = ["open", "high", "low", "close", "volume", "price"]

# ---------------------------------
# Operator mapping
# ---------------------------------
OPERATOR_MAP = {
    "greater than or equal to": ">=",
    "less than or equal to": "<=",
    "not equal to": "!=",
    "greater than": ">",
    "more than": ">",
    "above": ">",
    "less than": "<",
    "below": "<",
    "equal to": "==",
    "equals": "==",
    "is equal to": "==",
    "crosses above": "cross_above",
    "crosses below": "cross_below",
}

SORTED_OPERATORS = sorted(OPERATOR_MAP.keys(), key=len, reverse=True)

# ---------------------------------
# Number words
# ---------------------------------
NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50"
}

def normalize_number_words(text):
    """Convert number words to digits"""
    for w, n in NUMBER_WORDS.items():
        text = re.sub(rf"\b{w}\b", n, text, flags=re.IGNORECASE)
    return text

# ---------------------------------
# Number helpers
# ---------------------------------
def convert_suffix_numbers(t):
    """Convert 1m -> 1000000, 1k -> 1000"""
    t = str(t).strip().lower()
    t = t.replace(" million", "m").replace(" thousand", "k")
    
    for suf, mul in [("m", 1_000_000), ("k", 1_000)]:
        m = re.match(rf"(\d+(?:\.\d+)?){suf}\b", t)
        if m:
            return str(int(float(m.group(1)) * mul))
    return t

def clean_number_words(t):
    return str(t).replace(" million", "000000").replace(" thousand", "000")

# ---------------------------------
# Indicators
# ---------------------------------
def extract_indicator(expr):
    """Extract indicator patterns like RSI(14), SMA(20), 20-day moving average"""
    expr_lower = expr.lower().strip()
    expr_lower = re.sub(r"^the\s+", "", expr_lower)

    # Pattern 1: RSI(14), SMA(20), EMA(50)
    m = re.search(r"(rsi|sma|ema)\s*\(\s*(\d+)\s*\)", expr_lower)
    if m:
        return f"{m.group(1)}(close,{m.group(2)})"

    # Pattern 2: 20-day moving average, 20 day moving average, 20 days moving average
    m = re.search(r"(\d+)[- ]*days?\s+moving\s+average", expr_lower)
    if m:
        return f"sma(close,{m.group(1)})"
    
    # Pattern 3: moving average of 20 days
    m = re.search(r"moving\s+average\s+of\s+(\d+)", expr_lower)
    if m:
        return f"sma(close,{m.group(1)})"

    return expr

# ---------------------------------
# Time normalization
# ---------------------------------
def normalize_time_price(expr):
    """
    Convert time-based expressions to shift() or min()/max() notation
    Expects: number words already normalized, lowercase, apostrophes removed
    """
    expr_clean = expr.lower().strip()
    
    # Remove "the" prefix
    expr_clean = re.sub(r"^the\s+", "", expr_clean)

    # Pattern 1: yesterday/yesterdays + field
    m = re.search(r"yesterdays?\s+(open|high|low|close)", expr_clean)
    if m:
        return f"{m.group(1)}.shift(1)"

    # Pattern 2: last N days high/low
    m = re.search(r"last\s+(\d+)\s+days?\s+(high|low)", expr_clean)
    if m:
        days, field = m.groups()
        fn = "max" if field == "high" else "min"
        return f"{fn}({field},{days})"

    # Pattern 3: last N weeks high/low
    m = re.search(r"last\s+(\d+)\s+weeks?\s+(high|low)", expr_clean)
    if m:
        weeks, field = m.groups()
        days = int(weeks) * 5
        fn = "max" if field == "high" else "min"
        return f"{fn}({field},{days})"

    # Pattern 4: last week high/low (singular, assume 1 week)
    m = re.search(r"last\s+week\s+(high|low)", expr_clean)
    if m:
        field = m.group(1)
        fn = "max" if field == "high" else "min"
        return f"{fn}({field},5)"

    # Pattern 5: field from N days ago
    m = re.search(r"(open|high|low|close)\s+from\s+(\d+)\s+days?\s+ago", expr_clean)
    if m:
        field, days = m.groups()
        return f"{field}.shift({days})"

    # Pattern 6: N days ago field
    m = re.search(r"(\d+)\s+days?\s+ago\s+(high|low|open|close)", expr_clean)
    if m:
        days, field = m.groups()
        return f"{field}.shift({days})"

    return expr  # Return original if no match

# ---------------------------------
# Normalize functions
# ---------------------------------
def normalize_left_side(raw):
    """Normalize the left side of conditions"""
    raw = raw.lower().strip()

    if raw in ["price", "the price"]:
        return "close"
    
    if "close price" in raw:
        return "close"

    if re.search(r"(sma|ema|rsi|moving average)", raw):
        return extract_indicator(raw)

    for tok in raw.split():
        if tok in VALID_FIELDS:
            return tok

    return raw

def normalize_right_side(raw):
    """
    Normalize the right side of conditions
    Returns: Transformed value (indicator, shift, number, etc.)
    """
    # Clean and normalize
    text = raw.strip().lower()
    
    # Remove ALL apostrophes and quotes
    for char in ["'", "'", "'", "`", "´", '"', '"', '"']:
        text = text.replace(char, "")
    
    # Normalize number words (two -> 2)
    text = normalize_number_words(text)
    
    # Check for time patterns FIRST (most specific)
    if re.search(r"(yesterday|last\s+\d+|last\s+week|ago)", text):
        result = normalize_time_price(text)
        # If it transformed (doesn't contain "yesterday" or "last" anymore), return it
        if not re.search(r"(yesterday|last)", result):
            return result
    
    # Check for indicators
    if re.search(r"(moving\s+average|\d+[- ]*days?\s+moving|sma|ema|rsi)", text):
        result = extract_indicator(text)
        if result != text:
            return result
    
    # Try number suffix conversion (1m, 1k)
    result = convert_suffix_numbers(text)
    if result != text:
        text = result
    
    result = clean_number_words(text)
    if result != text:
        text = result
    
    # Convert to number if possible
    if not re.search(r'\w+\.\w+\(|\w+\(', text):
        try:
            num = float(text)
            return int(num) if num.is_integer() else num
        except:
            pass
    
    return text

# ---------------------------------
# Parsing helpers
# ---------------------------------
def protect_operators(text):
    """Replace operator phrases with tokens"""
    placeholders = {}
    tmp = text
    for i, phrase in enumerate(SORTED_OPERATORS):
        if phrase in tmp:
            token = f"__OP{i}__"
            tmp = tmp.replace(phrase, token)
            placeholders[token] = OPERATOR_MAP[phrase]
    return tmp, placeholders

def tokenize_logic(text):
    """Split by AND/OR while preserving them"""
    return [t.strip() for t in re.split(r"\b(and|or)\b", text, flags=re.IGNORECASE) if t.strip()]

def restore_operator(text, placeholders):
    """Convert protected operator tokens back to conditions"""
    for token, op in placeholders.items():
        if token in text:
            parts = text.split(token)
            if len(parts) != 2:
                continue
                
            left_raw, right_raw = parts
            left = normalize_left_side(left_raw.strip())
            right = normalize_right_side(right_raw.strip())
            
            return {"left": left, "operator": op, "right": right}
    
    return None

# ---------------------------------
# MAIN PARSER
# ---------------------------------
def parse_natural_language(text):
    """Main parser - converts natural language to structured JSON"""
    result = {
        "entry": {"conditions": [], "operators": []},
        "exit": {"conditions": [], "operators": []}
    }

    for sentence in re.split(r"[.;]", text.lower()):
        if not sentence.strip():
            continue

        # Determine rule type
        rule_type = None
        if any(k in sentence for k in ENTRY_KEYWORDS):
            rule_type = "entry"
        elif any(k in sentence for k in EXIT_KEYWORDS):
            rule_type = "exit"
        
        if not rule_type:
            continue

        # Special case: Percent change patterns
        pct = re.search(
            r"(\w+)\s+increases?\s+by\s+more\s+than\s+(\d+)\s*percent\s+compared\s+to\s+last\s+(\d+)\s+(days?|weeks?)",
            sentence
        )
        if pct:
            field, val, num, unit = pct.groups()
            days = int(num) * (5 if 'week' in unit else 1)
            result[rule_type]["conditions"].append({
                "left": f"pct_change({field},{days})",
                "operator": ">",
                "right": float(val)
            })
            continue
        
        pct_week = re.search(
            r"(\w+)\s+increases?\s+by\s+more\s+than\s+(\d+)\s*percent\s+compared\s+to\s+last\s+week",
            sentence
        )
        if pct_week:
            field, val = pct_week.groups()
            result[rule_type]["conditions"].append({
                "left": f"pct_change({field},5)",
                "operator": ">",
                "right": float(val)
            })
            continue

        # Remove keywords
        for k in ENTRY_KEYWORDS + EXIT_KEYWORDS:
            sentence = sentence.replace(k, "")
        sentence = sentence.replace("when", "").strip()

        # Protect operators and tokenize
        protected, placeholders = protect_operators(sentence)
        tokens = tokenize_logic(protected)

        # Process tokens
        for tok in tokens:
            if tok.upper() in ["AND", "OR"]:
                result[rule_type]["operators"].append(tok.upper())
                continue

            cond = restore_operator(tok, placeholders)
            if cond:
                result[rule_type]["conditions"].append(cond)

    return result

# ---------------------------------
# TEST SUITE
# ---------------------------------
if __name__ == "__main__":
    tests = [
        "Buy when the close price is above the 20-day moving average and volume is above 1 million.",
        "Enter when price crosses above yesterday's high.",
        "Exit when RSI(14) is below 30.",
        "Trigger entry when volume increases by more than 30 percent compared to last week.",
        "Enter when price crosses above last two days high.",
        "Buy when close is above last 5 days high.",
    ]

    print("=" * 80)
    print("NL_PARSER.PY - TEST SUITE")
    print("=" * 80)

    for i, test in enumerate(tests, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {test}")
        print(f"{'='*80}")
        result = parse_natural_language(test)
        print(json.dumps(result, indent=2))
        
        # Validation
        if i == 2 and result['entry']['conditions']:
            right = result['entry']['conditions'][0]['right']
            if right == "high.shift(1)":
                print("✅ PASS: yesterday's high -> high.shift(1)")
            else:
                print(f"❌ FAIL: Got '{right}'")
        
        if i == 5 and result['entry']['conditions']:
            right = result['entry']['conditions'][0]['right']
            if right == "max(high,2)":
                print("✅ PASS: last two days high -> max(high,2)")
            else:
                print(f"❌ FAIL: Got '{right}'")

    print("\n" + "=" * 80)