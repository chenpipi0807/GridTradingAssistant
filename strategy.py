"""
策略模块 - 负责实现交易策略和回测
"""
import pandas as pd
import numpy as np
from datetime import datetime


class TradingStrategy:
    def __init__(self):
        """初始化交易策略"""
        pass
    
    def mid_price_trading(self, df, upper_pct=0.01, lower_pct=0.01, initial_capital=100000, fee_rate=0.0003):
        """
        中间价交易策略：在中间价下方买入，上方卖出
        
        Parameters:
        -----------
        df : pd.DataFrame
            处理后的股票数据，需包含'mid_price', 'high', 'low', 'close'列
        upper_pct : float
            上轨百分比，默认1%
        lower_pct : float
            下轨百分比，默认1%
        initial_capital : float
            初始资金，默认10万
        fee_rate : float
            交易费率，默认0.03%
            
        Returns:
        --------
        dict : 包含回测结果的字典
        """
        if df.empty or len(df) < 2:
            return {
                'total_return': 0,
                'total_trades': 0,
                'win_rate': 0,
                'trades': []
            }
        
        # 确保数据按日期排序
        df = df.sort_values('date').reset_index(drop=True)
        
        # 创建结果容器
        trades = []
        positions = []  # 持仓记录
        capital = initial_capital  # 当前资金
        shares = 0  # 持有股票数量
        cost_basis = 0  # 持仓成本
        
        # 遍历每一天的数据
        for i in range(len(df)):
            date = df.iloc[i]['date']
            mid_price = df.iloc[i]['mid_price']
            high_price = df.iloc[i]['high']
            low_price = df.iloc[i]['low']
            close_price = df.iloc[i]['close']
            
            # 计算中间价通道
            upper_price = mid_price * (1 + upper_pct)
            lower_price = mid_price * (1 - lower_pct)
            
            # 交易逻辑
            # 情况1：当天最高价超过上轨，考虑卖出
            if high_price >= upper_price and shares > 0:
                # 计算卖出金额（扣除手续费）
                sell_price = upper_price
                sell_amount = shares * sell_price
                fee = sell_amount * fee_rate
                net_amount = sell_amount - fee
                
                # 更新资金和持仓
                profit = net_amount - cost_basis
                capital += net_amount
                
                # 记录交易
                trades.append({
                    'date': date,
                    'type': 'sell',
                    'price': sell_price,
                    'shares': shares,
                    'amount': sell_amount,
                    'fee': fee,
                    'profit': profit
                })
                
                # 清空持仓
                shares = 0
                cost_basis = 0
                
            # 情况2：当天最低价低于下轨，考虑买入
            elif low_price <= lower_price and shares == 0 and capital > 0:
                # 计算可买入的股数（考虑手续费，取整数）
                buy_price = lower_price
                max_shares = int(capital / (buy_price * (1 + fee_rate)))
                
                if max_shares > 0:
                    # 计算买入金额
                    buy_amount = max_shares * buy_price
                    fee = buy_amount * fee_rate
                    total_cost = buy_amount + fee
                    
                    # 更新资金和持仓
                    capital -= total_cost
                    shares = max_shares
                    cost_basis = total_cost
                    
                    # 记录交易
                    trades.append({
                        'date': date,
                        'type': 'buy',
                        'price': buy_price,
                        'shares': shares,
                        'amount': buy_amount,
                        'fee': fee,
                        'cost': total_cost
                    })
            
            # 记录每日持仓情况
            positions.append({
                'date': date,
                'shares': shares,
                'capital': capital,
                'close_price': close_price,
                'position_value': shares * close_price,
                'total_value': capital + (shares * close_price)
            })
        
        # 计算回测结果
        position_df = pd.DataFrame(positions)
        
        # 如果最后还有持仓，按收盘价计算最终价值
        if shares > 0:
            final_value = capital + (shares * df.iloc[-1]['close'])
        else:
            final_value = capital
            
        total_return_pct = (final_value / initial_capital - 1) * 100
        
        # 计算每笔交易的盈亏
        win_trades = [t for t in trades if t['type'] == 'sell' and t['profit'] > 0]
        loss_trades = [t for t in trades if t['type'] == 'sell' and t['profit'] <= 0]
        
        win_rate = len(win_trades) / max(len(win_trades) + len(loss_trades), 1)
        
        # 整合回测结果
        backtest_result = {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return_pct,
            'total_trades': len([t for t in trades if t['type'] == 'buy']),
            'win_trades': len(win_trades),
            'loss_trades': len(loss_trades),
            'win_rate': win_rate,
            'trades': trades,
            'daily_positions': position_df.to_dict('records')
        }
        
        return backtest_result
    
    def analyze_backtest(self, df, backtest_result):
        """
        分析回测结果
        
        Parameters:
        -----------
        df : pd.DataFrame
            原始股票数据
        backtest_result : dict
            回测结果
            
        Returns:
        --------
        dict : 带有分析指标的回测结果
        """
        if not backtest_result or 'daily_positions' not in backtest_result:
            return backtest_result
            
        positions = pd.DataFrame(backtest_result['daily_positions'])
        
        if positions.empty:
            return backtest_result
            
        # 计算日收益率
        positions['daily_return'] = positions['total_value'].pct_change() * 100
        
        # 计算累计收益率
        positions['cumulative_return'] = (positions['total_value'] / positions['total_value'].iloc[0] - 1) * 100
        
        # 计算最大回撤
        positions['peak'] = positions['total_value'].cummax()
        positions['drawdown'] = (positions['total_value'] / positions['peak'] - 1) * 100
        max_drawdown = positions['drawdown'].min()
        
        # 计算夏普比率（假设无风险收益率为3%）
        risk_free_rate = 0.03 / 252  # 日化的无风险收益率
        daily_excess_return = positions['daily_return'] / 100 - risk_free_rate
        sharpe_ratio = np.sqrt(252) * daily_excess_return.mean() / daily_excess_return.std() if daily_excess_return.std() > 0 else 0
        
        # 更新回测结果
        backtest_result.update({
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_daily_return': positions['daily_return'].mean(),
            'volatility': positions['daily_return'].std(),
            'positions': positions.to_dict('records')
        })
        
        return backtest_result
    
    def optimize_parameters(self, df, upper_pct_range=(0.005, 0.02, 0.005), lower_pct_range=(0.005, 0.02, 0.005)):
        """
        参数优化：寻找最优的上下轨百分比
        
        Parameters:
        -----------
        df : pd.DataFrame
            处理后的股票数据
        upper_pct_range : tuple
            上轨百分比范围(起始值, 结束值, 步长)
        lower_pct_range : tuple
            下轨百分比范围(起始值, 结束值, 步长)
            
        Returns:
        --------
        dict : 参数优化结果
        """
        if df.empty or len(df) < 10:
            return {
                'best_params': {
                    'upper_pct': 0.01,
                    'lower_pct': 0.01
                },
                'best_return': 0,
                'all_results': []
            }
        
        # 参数网格
        upper_values = np.arange(upper_pct_range[0], upper_pct_range[1] + 0.0001, upper_pct_range[2])
        lower_values = np.arange(lower_pct_range[0], lower_pct_range[1] + 0.0001, lower_pct_range[2])
        
        # 储存所有回测结果
        all_results = []
        best_return = -float('inf')
        best_params = {'upper_pct': 0.01, 'lower_pct': 0.01}
        
        # 网格搜索
        for upper_pct in upper_values:
            for lower_pct in lower_values:
                # 运行回测
                result = self.mid_price_trading(df, upper_pct, lower_pct)
                
                # 记录结果
                params_result = {
                    'upper_pct': upper_pct,
                    'lower_pct': lower_pct,
                    'total_return': result['total_return'],
                    'total_trades': result['total_trades'],
                    'win_rate': result['win_rate']
                }
                all_results.append(params_result)
                
                # 更新最优参数
                if result['total_return'] > best_return:
                    best_return = result['total_return']
                    best_params = {'upper_pct': upper_pct, 'lower_pct': lower_pct}
        
        # 返回优化结果
        return {
            'best_params': best_params,
            'best_return': best_return,
            'all_results': all_results
        }
    
    def generate_alerts(self, df, window=5, amplitude_threshold=90, price_change_threshold=0.02):
        """
        生成交易预警
        
        Parameters:
        -----------
        df : pd.DataFrame
            处理后的股票数据
        window : int
            历史窗口大小
        amplitude_threshold : float
            振幅百分位阈值
        price_change_threshold : float
            价格变化阈值
            
        Returns:
        --------
        list : 预警列表
        """
        if df.empty or len(df) < window:
            return []
            
        alerts = []
        latest_data = df.iloc[-1]
        latest_date = latest_data['date']
        
        # 检查价格突破历史区间
        hist_data = df.iloc[-window-1:-1]  # 不包括当天的历史数据
        hist_high = hist_data['high'].max()
        hist_low = hist_data['low'].min()
        
        current_close = latest_data['close']
        
        # 检查上突破
        if current_close > hist_high * (1 + price_change_threshold):
            alerts.append({
                'type': 'price_breakout',
                'direction': 'up',
                'date': latest_date,
                'message': f"价格上突破: 当前价 {current_close:.2f} 突破历史{window}日最高价 {hist_high:.2f}",
                'level': 'warning'
            })
            
        # 检查下突破
        elif current_close < hist_low * (1 - price_change_threshold):
            alerts.append({
                'type': 'price_breakout',
                'direction': 'down',
                'date': latest_date,
                'message': f"价格下突破: 当前价 {current_close:.2f} 跌破历史{window}日最低价 {hist_low:.2f}",
                'level': 'warning'
            })
            
        # 检查异常振幅
        if 'amplitude_percentile' in latest_data and latest_data['amplitude_percentile'] > amplitude_threshold:
            alerts.append({
                'type': 'amplitude_alert',
                'date': latest_date,
                'message': f"振幅异常: 当前振幅 {latest_data['amplitude']:.2f}% (历史{amplitude_threshold}百分位)",
                'level': 'warning'
            })
            
        # 检查资金异动
        if 'main_net_inflow' in latest_data and abs(latest_data['main_net_inflow']) > 1000000:  # 超过100万
            direction = '流入' if latest_data['main_net_inflow'] > 0 else '流出'
            amount_mil = abs(latest_data['main_net_inflow'] / 10000)
            alerts.append({
                'type': 'fund_flow_alert',
                'direction': 'in' if latest_data['main_net_inflow'] > 0 else 'out',
                'date': latest_date,
                'message': f"资金异动: 主力资金{direction} {amount_mil:.2f}万",
                'level': 'info' if direction == '流入' else 'warning'
            })
            
        return alerts
