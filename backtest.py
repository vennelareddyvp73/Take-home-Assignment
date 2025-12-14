import pandas as pd
import numpy as np
from typing import Dict, List, Optional


def backtest(df: pd.DataFrame, 
             signals: pd.DataFrame, 
             initial_cash: float = 100000,
             commission: float = 0.001) -> Dict:

    
    # Validation
    if len(df) != len(signals):
        raise ValueError("DataFrame and signals must have same length")
    if 'close' not in df.columns:
        raise ValueError("DataFrame must contain 'close' column")
    if not all(col in signals.columns for col in ['entry', 'exit']):
        raise ValueError("Signals must contain 'entry' and 'exit' columns")
    
    # Initialize state
    position = 0.0
    entry_price = 0.0
    entry_date = None
    entry_index = None
    trades = []
    equity_curve = []
    cash = initial_cash
    
    # Main backtest loop
    for i in range(len(df)):
        # Get current data using iloc for positional indexing
        date = df.iloc[i]['date'] if 'date' in df.columns else df.index[i]
        price = df.iloc[i]['close']
        
        # Get signals
        entry_signal = signals.iloc[i]['entry']
        exit_signal = signals.iloc[i]['exit']
        
        # ENTRY LOGIC
        if entry_signal and position == 0:
            # Calculate position size (fully invest after commission)
            position = cash / (price * (1 + commission))
            entry_price = price
            entry_date = date
            entry_index = i
            
            # Deduct commission
            cash = 0
        
        # EXIT LOGIC
        elif exit_signal and position > 0:
            exit_price = price
            exit_date = date
            
            # Calculate trade P&L after commission
            gross_proceeds = position * exit_price
            commission_cost = gross_proceeds * commission
            net_proceeds = gross_proceeds - commission_cost
            
            profit = net_proceeds - (position * entry_price)
            return_pct = (exit_price / entry_price - 1) * 100
            
            # Record trade
            trades.append({
                "entry_date": entry_date,
                "exit_date": exit_date,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "position_size": position,
                "profit": profit,
                "return_pct": return_pct
            })
            
            cash = net_proceeds
            position = 0
            entry_price = 0
        
        # Update equity curve
        current_equity = cash if position == 0 else (position * price)
        equity_curve.append(current_equity)
    
    # Handle open position at end
    if position > 0:
        exit_price = df['close'].iloc[-1]
        exit_date = df['date'].iloc[-1] if 'date' in df.columns else df.index[-1]
        
        gross_proceeds = position * exit_price
        commission_cost = gross_proceeds * commission
        net_proceeds = gross_proceeds - commission_cost
        
        profit = net_proceeds - (position * entry_price)
        return_pct = (exit_price / entry_price - 1) * 100
        
        trades.append({
            "entry_date": entry_date,
            "exit_date": exit_date,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "position_size": position,
            "profit": profit,
            "return_pct": return_pct,
            "status": "open_at_end"
        })
        
        cash = net_proceeds
        position = 0
        equity_curve[-1] = cash
    
    # Calculate comprehensive metrics
    final_cash = cash
    total_return = (final_cash - initial_cash) / initial_cash * 100
    
    # Equity curve analysis
    equity_curve = np.array(equity_curve)
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve / running_max - 1) * 100
    max_drawdown = drawdown.min()
    
    # Trade statistics
    num_trades = len(trades)
    
    if num_trades > 0:
        profits = [t['profit'] for t in trades]
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p < 0]
        
        win_rate = len(winning_trades) / num_trades * 100 if num_trades > 0 else 0
        
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_trade_return = np.mean([t['return_pct'] for t in trades])
        avg_winning_trade = np.mean(winning_trades) if winning_trades else 0
        avg_losing_trade = np.mean(losing_trades) if losing_trades else 0
    else:
        win_rate = 0
        profit_factor = 0
        avg_trade_return = 0
        avg_winning_trade = 0
        avg_losing_trade = 0
        gross_profit = 0
        gross_loss = 0
    
    # Sharpe ratio (simplified - assumes daily data)
    if len(equity_curve) > 1:
        returns = np.diff(equity_curve) / equity_curve[:-1]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    else:
        sharpe_ratio = 0
    
    return {
        "trades": trades,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "num_trades": num_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade_return": avg_trade_return,
        "avg_winning_trade": avg_winning_trade,
        "avg_losing_trade": avg_losing_trade,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "sharpe_ratio": sharpe_ratio,
        "equity_curve": equity_curve,
        "final_cash": final_cash,
        "initial_cash": initial_cash
    }


def print_backtest_summary(result: Dict) -> None:
    """
    Print a formatted summary of backtest results.
    """
    # Print trades FIRST for clarity
    if result['trades']:
        print("\n" + "="*80)
        print(" TRADE HISTORY")
        print("="*80)
        print(f"\nTotal Trades: {result['num_trades']}\n")
        print("-"*80)
        
        for i, trade in enumerate(result['trades'], 1):
            status = trade.get('status', 'closed')
            profit_sign = "✅" if trade['profit'] > 0 else "❌"
            
            print(f"\n{profit_sign} Trade #{i}:")
            print(f"  Entry Date:       {trade['entry_date']}")
            print(f"  Exit Date:        {trade['exit_date']}")
            print(f"  Entry Price:      ${trade['entry_price']:.2f}")
            print(f"  Exit Price:       ${trade['exit_price']:.2f}")
            print(f"  Profit/Loss:      ${trade['profit']:,.2f} ({trade['return_pct']:+.2f}%)")
            if status != 'closed':
                print(f"  Status:           {status.upper()}")
            print("-"*80)
    
    # Then print summary metrics
    print("\n" + "="*80)
    print(" BACKTEST RESULTS SUMMARY")
    print("="*80)
    
    print(f"\n Portfolio Performance:")
    print(f"  Initial Capital:        ${result['initial_cash']:,.2f}")
    print(f"  Final Capital:          ${result['final_cash']:,.2f}")
    print(f"  Total Return:           {result['total_return']:,.2f}%")
    print(f"  Max Drawdown:           {result['max_drawdown']:,.2f}%")
    print(f"  Number of Trades:       {result['num_trades']}")
    
    print("\n" + "="*80)

