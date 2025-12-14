
import sys
import importlib

for module in ['nl_parser', 'dsl_generator', 'dsl_parser', 'python_code_generator', 'backtest']:
    if module in sys.modules:
        importlib.reload(sys.modules[module])

import pandas as pd
from pprint import pprint

# Import from your modules
from nl_parser import parse_natural_language
from dsl_generator import generate_dsl
from dsl_parser import parse_dsl
from python_code_generator import generate_strategy
from backtest import backtest, print_backtest_summary


def print_section_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main():
    """
    Main execution pipeline:
    NL Input → JSON → DSL → AST → Strategy → Backtest → Report
    """
    
    print_section_header("STEP 1: Natural Language Input")
    
    nl_input = input("\nEnter your trading strategy in plain English:\n(or press Enter for default)\n> ")
    
    if not nl_input.strip():
        nl_input = "Buy when price closes above the 20-day moving average and volume is above 1M."
    
    print(f"\n Input: {nl_input}")
    

    print_section_header("STEP 2: Parse Natural Language to JSON")
    
    parsed_json = parse_natural_language(nl_input)
    print("\n Parsed JSON Structure:")
    pprint(parsed_json)
    

    print_section_header("STEP 3: Generate DSL Text")
    
    try:
        dsl_text = generate_dsl(parsed_json)
        print("\n Generated DSL:")
        print(dsl_text)
    except ValueError as e:
        print(f"\n DSL Generation Error: {e}")
        return
    

    print_section_header("STEP 4: Parse DSL to AST")
    
    try:
        ast = parse_dsl(dsl_text)
        print("\n Generated AST:")
        pprint(ast)
    except SyntaxError as e:
        print(f"\n DSL Parse Error: {e}")
        return
    

    print_section_header("STEP 5: Load Market Data")
    
    try:
        df = pd.read_csv("ohlcv.csv")
        print(f"\n Loaded {len(df)} rows of OHLCV data")
        print("\nFirst 5 rows:")
        print(df.head())
        print("\nLast 5 rows:")
        print(df.tail())
    except FileNotFoundError:
        print("\n Error: ohlcv.csv not found!")
        print("Please create ohlcv.csv with columns: date,open,high,low,close,volume")
        return
    

    print_section_header("STEP 6: Generate Trading Strategy")
    
    strategy_fn = generate_strategy(ast)
    signals = strategy_fn(df)
    
    print("\n Strategy generated successfully!")
    print(f"\n Signal Summary:")
    print(f"  Total Entry Signals:  {signals['entry'].sum()}")
    print(f"  Total Exit Signals:   {signals['exit'].sum()}")
    
    # Show sample signals
    signal_dates = signals[signals['entry'] | signals['exit']]
    if len(signal_dates) > 0:
        print("\n Sample Signals (first 5):")
        for idx in signal_dates.head().index:
            date = df.iloc[idx]['date'] if 'date' in df.columns else idx
            entry = "ENTRY" if signals.iloc[idx]['entry'] else ""
            exit = "EXIT" if signals.iloc[idx]['exit'] else ""
            signal = entry or exit
            print(f"  {date}: {signal}")
    

    print_section_header("STEP 7: Execute Backtest")
    
    result = backtest(df, signals, initial_cash=100000, commission=0.001)
    
    print("\nBacktest completed!")
    

    print_section_header("STEP 8: Backtest Results")
    
    print_backtest_summary(result)
    
    print("\n" + "=" * 80)
    print(" EXECUTION SUMMARY")
    print("=" * 80)
    
    print(f"\n Natural Language: {nl_input}")
    print(f" DSL Generated: Success")
    print(f" AST Parsed: Success")
    print(f" Strategy Executed: Success")
    print(f" Backtest Completed: Success")
    
    print(f"\n Final Results:")
    print(f"   Total Return:    {result['total_return']:>8.2f}%")
    print(f"   Max Drawdown:    {result['max_drawdown']:>8.2f}%")
    print(f"   Number of Trades: {result['num_trades']:>7}")
    


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user.")
    except Exception as e:
        print(f"\n\n Unexpected error: {e}")
        import traceback
        traceback.print_exc()