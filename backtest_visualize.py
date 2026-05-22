"""
Backtest Visualization
Generate charts and visual reports from backtest results
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from datetime import datetime

# Set style
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

RESULTS_FOLDER = "backtest_results"


def load_results():
    """Load backtest results"""
    # Load trades
    trades_file = os.path.join(RESULTS_FOLDER, 'trades_log.csv')
    trades_df = pd.read_csv(trades_file)
    trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date'])
    trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date'])
    
    # Load metrics
    metrics_file = os.path.join(RESULTS_FOLDER, 'performance_summary.json')
    with open(metrics_file, 'r') as f:
        metrics = json.load(f)
    
    # Load equity curve
    equity_file = os.path.join(RESULTS_FOLDER, 'equity_curve.csv')
    equity_df = pd.read_csv(equity_file)
    equity_df['date'] = pd.to_datetime(equity_df['date'])
    
    return trades_df, metrics, equity_df


def plot_equity_curve(equity_df, metrics):
    """Plot equity curve over time"""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    ax.plot(equity_df['date'], equity_df['equity'], linewidth=2, color='#047857', label='Portfolio Value')
    ax.axhline(y=metrics['initial_capital'], color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    
    ax.set_title('Portfolio Equity Curve', fontsize=16, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Portfolio Value (₹)', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Format y-axis as currency
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x/100000:.1f}L'))
    
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_FOLDER, 'equity_curve.png'), dpi=300, bbox_inches='tight')
    print("✅ Equity curve chart saved")
    plt.close()


def plot_pnl_distribution(trades_df):
    """Plot P&L distribution"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Histogram of P&L percentage
    ax1.hist(trades_df['pnl_percent'], bins=30, color='#047857', alpha=0.7, edgecolor='black')
    ax1.axvline(x=0, color='red', linestyle='--', linewidth=2)
    ax1.set_title('P&L Distribution (%)', fontsize=14, fontweight='bold')
    ax1.set_xlabel('P&L (%)', fontsize=12)
    ax1.set_ylabel('Number of Trades', fontsize=12)
    ax1.grid(True, alpha=0.3)
    
    # Box plot by exit reason
    exit_reasons = trades_df.groupby('exit_reason')['pnl_percent'].apply(list).to_dict()
    ax2.boxplot(exit_reasons.values(), labels=exit_reasons.keys())
    ax2.axhline(y=0, color='red', linestyle='--', linewidth=1)
    ax2.set_title('P&L by Exit Reason', fontsize=14, fontweight='bold')
    ax2.set_ylabel('P&L (%)', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_FOLDER, 'pnl_distribution.png'), dpi=300, bbox_inches='tight')
    print("✅ P&L distribution chart saved")
    plt.close()


def plot_win_loss_analysis(trades_df):
    """Plot win/loss analysis"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    # Exit reason pie chart
    exit_counts = trades_df['exit_reason'].value_counts()
    colors = {'TARGET': '#047857', 'STOPLOSS': '#DC2626', 'TIMEOUT': '#D97706', 'BACKTEST_END': '#6B7280'}
    ax1.pie(exit_counts.values, labels=exit_counts.index, autopct='%1.1f%%', 
            colors=[colors.get(x, '#6B7280') for x in exit_counts.index], startangle=90)
    ax1.set_title('Exit Reasons Distribution', fontsize=14, fontweight='bold')
    
    # P&L by entry quality
    entry_quality_pnl = trades_df.groupby('entry_quality')['pnl_percent'].mean().sort_values()
    ax2.barh(entry_quality_pnl.index, entry_quality_pnl.values, color='#047857')
    ax2.axvline(x=0, color='red', linestyle='--', linewidth=1)
    ax2.set_title('Average P&L by Entry Quality', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Average P&L (%)', fontsize=12)
    ax2.grid(True, alpha=0.3, axis='x')
    
    # Holding period distribution
    ax3.hist(trades_df['holding_days'], bins=20, color='#047857', alpha=0.7, edgecolor='black')
    ax3.set_title('Holding Period Distribution', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Days Held', fontsize=12)
    ax3.set_ylabel('Number of Trades', fontsize=12)
    ax3.grid(True, alpha=0.3)
    
    # Cumulative P&L over time
    trades_sorted = trades_df.sort_values('exit_date')
    trades_sorted['cumulative_pnl'] = trades_sorted['pnl_amount'].cumsum()
    ax4.plot(trades_sorted['exit_date'], trades_sorted['cumulative_pnl'], linewidth=2, color='#047857')
    ax4.axhline(y=0, color='red', linestyle='--', linewidth=1)
    ax4.set_title('Cumulative P&L Over Time', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Date', fontsize=12)
    ax4.set_ylabel('Cumulative P&L (₹)', fontsize=12)
    ax4.grid(True, alpha=0.3)
    ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x/100000:.1f}L'))
    
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_FOLDER, 'win_loss_analysis.png'), dpi=300, bbox_inches='tight')
    print("✅ Win/Loss analysis chart saved")
    plt.close()


def plot_fibonacci_analysis(trades_df):
    """Plot Fibonacci level analysis"""
    # Filter trades with Fibonacci
    fib_trades = trades_df[trades_df['has_fibonacci'] == True].copy()
    
    if len(fib_trades) == 0:
        print("⚠️ No Fibonacci trades found, skipping chart")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # P&L by Fibonacci level
    fib_level_pnl = fib_trades.groupby('fibonacci_level')['pnl_percent'].mean().sort_values()
    ax1.barh(fib_level_pnl.index, fib_level_pnl.values, color='#047857')
    ax1.axvline(x=0, color='red', linestyle='--', linewidth=1)
    ax1.set_title('Average P&L by Fibonacci Level', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Average P&L (%)', fontsize=12)
    ax1.grid(True, alpha=0.3, axis='x')
    
    # Win rate by Fibonacci level
    fib_level_wins = fib_trades.groupby('fibonacci_level').apply(
        lambda x: (x['exit_reason'] == 'TARGET').sum() / len(x) * 100
    ).sort_values()
    ax2.barh(fib_level_wins.index, fib_level_wins.values, color='#047857')
    ax2.set_title('Win Rate by Fibonacci Level', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Win Rate (%)', fontsize=12)
    ax2.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_FOLDER, 'fibonacci_analysis.png'), dpi=300, bbox_inches='tight')
    print("✅ Fibonacci analysis chart saved")
    plt.close()


def generate_summary_report(trades_df, metrics):
    """Generate text summary report"""
    report = []
    report.append("=" * 80)
    report.append("STOCK YARD BACKTEST SUMMARY REPORT")
    report.append("=" * 80)
    report.append("")
    
    report.append("📊 OVERALL PERFORMANCE")
    report.append("-" * 80)
    report.append(f"Initial Capital:        ₹{metrics['initial_capital']:,.2f}")
    report.append(f"Final Equity:           ₹{metrics['final_equity']:,.2f}")
    report.append(f"Total Return:           {metrics['total_return_percent']:+.2f}%")
    report.append(f"Total P&L:              ₹{metrics['total_pnl']:,.2f}")
    report.append("")
    
    report.append("📈 TRADE STATISTICS")
    report.append("-" * 80)
    report.append(f"Total Trades:           {metrics['total_trades']}")
    report.append(f"Winners (Target):       {metrics['winners']} ({metrics['win_rate']:.1f}%)")
    report.append(f"Losers (Stop-Loss):     {metrics['losers']}")
    report.append(f"Timeouts:               {metrics['timeouts']}")
    report.append(f"Average Holding:        {metrics['avg_holding_days']:.1f} days")
    report.append("")
    
    report.append("💰 PROFIT & LOSS METRICS")
    report.append("-" * 80)
    report.append(f"Average Win:            ₹{metrics['avg_win']:,.2f}")
    report.append(f"Average Loss:           ₹{metrics['avg_loss']:,.2f}")
    report.append(f"Profit Factor:          {metrics['profit_factor']:.2f}")
    report.append(f"Sharpe Ratio:           {metrics['sharpe_ratio']:.2f}")
    report.append(f"Max Drawdown:           {metrics['max_drawdown_percent']:.2f}%")
    report.append("")
    
    # Top winners
    report.append("🏆 TOP 5 WINNING TRADES")
    report.append("-" * 80)
    top_winners = trades_df.nlargest(5, 'pnl_amount')
    for idx, trade in top_winners.iterrows():
        report.append(f"{trade['symbol']:12} | Entry: ₹{trade['entry_price']:8.2f} | Exit: ₹{trade['exit_price']:8.2f} | P&L: {trade['pnl_percent']:+6.2f}% (₹{trade['pnl_amount']:+,.0f})")
    report.append("")
    
    # Top losers
    report.append("📉 TOP 5 LOSING TRADES")
    report.append("-" * 80)
    top_losers = trades_df.nsmallest(5, 'pnl_amount')
    for idx, trade in top_losers.iterrows():
        report.append(f"{trade['symbol']:12} | Entry: ₹{trade['entry_price']:8.2f} | Exit: ₹{trade['exit_price']:8.2f} | P&L: {trade['pnl_percent']:+6.2f}% (₹{trade['pnl_amount']:+,.0f})")
    report.append("")
    
    report.append("=" * 80)
    
    # Save report
    report_file = os.path.join(RESULTS_FOLDER, 'summary_report.txt')
    with open(report_file, 'w') as f:
        f.write('\n'.join(report))
    
    print("✅ Summary report saved")
    
    # Also print to console
    print("\n" + '\n'.join(report))


def main():
    """Generate all visualizations"""
    print("=" * 80)
    print("📊 GENERATING BACKTEST VISUALIZATIONS")
    print("=" * 80)
    print()
    
    # Load results
    print("📂 Loading backtest results...")
    trades_df, metrics, equity_df = load_results()
    print(f"✅ Loaded {len(trades_df)} trades")
    print()
    
    # Generate charts
    print("📈 Generating charts...")
    plot_equity_curve(equity_df, metrics)
    plot_pnl_distribution(trades_df)
    plot_win_loss_analysis(trades_df)
    plot_fibonacci_analysis(trades_df)
    print()
    
    # Generate summary report
    print("📝 Generating summary report...")
    generate_summary_report(trades_df, metrics)
    print()
    
    print("=" * 80)
    print("✅ All visualizations generated successfully!")
    print(f"📁 Check {RESULTS_FOLDER}/ folder for all charts and reports")
    print("=" * 80)


if __name__ == "__main__":
    main()
