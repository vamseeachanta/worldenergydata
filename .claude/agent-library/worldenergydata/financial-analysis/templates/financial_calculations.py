"""
Financial Analysis Calculations Template
Comprehensive financial calculations for investment analysis, valuation, and risk management
"""

import numpy as np
import pandas as pd
from scipy import stats, optimize
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta


# ==============================================================================
# Valuation Models
# ==============================================================================

def dcf_valuation(
    free_cash_flows: List[float],
    terminal_growth_rate: float,
    wacc: float,
    terminal_year: int = 5
) -> Dict[str, float]:
    """
    Discounted Cash Flow valuation model
    
    Args:
        free_cash_flows: List of projected free cash flows
        terminal_growth_rate: Perpetual growth rate for terminal value
        wacc: Weighted Average Cost of Capital
        terminal_year: Year for terminal value calculation
    
    Returns:
        Dictionary with enterprise value and components
    """
    # Present value of explicit forecast period
    pv_fcf = sum([fcf / (1 + wacc) ** (i + 1) 
                  for i, fcf in enumerate(free_cash_flows)])
    
    # Terminal value
    terminal_fcf = free_cash_flows[-1] * (1 + terminal_growth_rate)
    terminal_value = terminal_fcf / (wacc - terminal_growth_rate)
    pv_terminal = terminal_value / (1 + wacc) ** terminal_year
    
    # Enterprise value
    enterprise_value = pv_fcf + pv_terminal
    
    return {
        'enterprise_value': enterprise_value,
        'pv_fcf': pv_fcf,
        'terminal_value': terminal_value,
        'pv_terminal': pv_terminal,
        'implied_multiple': terminal_value / free_cash_flows[-1]
    }


def calculate_wacc(
    market_cap: float,
    debt_value: float,
    cost_of_equity: float,
    cost_of_debt: float,
    tax_rate: float
) -> float:
    """
    Calculate Weighted Average Cost of Capital
    
    Args:
        market_cap: Market value of equity
        debt_value: Market value of debt
        cost_of_equity: Required return on equity
        cost_of_debt: Interest rate on debt
        tax_rate: Corporate tax rate
    
    Returns:
        WACC as decimal
    """
    total_value = market_cap + debt_value
    equity_weight = market_cap / total_value
    debt_weight = debt_value / total_value
    
    wacc = (equity_weight * cost_of_equity + 
            debt_weight * cost_of_debt * (1 - tax_rate))
    
    return wacc


def capm_cost_of_equity(
    risk_free_rate: float,
    beta: float,
    market_return: float
) -> float:
    """
    Calculate cost of equity using CAPM
    
    Args:
        risk_free_rate: Risk-free rate (e.g., 10-year Treasury)
        beta: Stock's beta coefficient
        market_return: Expected market return
    
    Returns:
        Cost of equity as decimal
    """
    return risk_free_rate + beta * (market_return - risk_free_rate)


def relative_valuation(
    metric_value: float,
    peer_multiples: List[float],
    adjustment_factor: float = 1.0
) -> Dict[str, float]:
    """
    Relative valuation using peer multiples
    
    Args:
        metric_value: Company's metric (EBITDA, Revenue, etc.)
        peer_multiples: List of peer company multiples
        adjustment_factor: Company-specific adjustment
    
    Returns:
        Valuation statistics
    """
    peer_median = np.median(peer_multiples)
    peer_mean = np.mean(peer_multiples)
    peer_25th = np.percentile(peer_multiples, 25)
    peer_75th = np.percentile(peer_multiples, 75)
    
    implied_value_median = metric_value * peer_median * adjustment_factor
    implied_value_mean = metric_value * peer_mean * adjustment_factor
    
    return {
        'implied_value_median': implied_value_median,
        'implied_value_mean': implied_value_mean,
        'implied_value_25th': metric_value * peer_25th * adjustment_factor,
        'implied_value_75th': metric_value * peer_75th * adjustment_factor,
        'peer_median_multiple': peer_median,
        'peer_mean_multiple': peer_mean
    }


# ==============================================================================
# Portfolio Analytics
# ==============================================================================

def portfolio_optimization(
    returns: pd.DataFrame,
    risk_free_rate: float = 0.02,
    target_return: Optional[float] = None
) -> Dict[str, np.ndarray]:
    """
    Markowitz portfolio optimization
    
    Args:
        returns: DataFrame of asset returns
        risk_free_rate: Risk-free rate for Sharpe ratio
        target_return: Target portfolio return (optional)
    
    Returns:
        Optimal weights and portfolio metrics
    """
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    n_assets = len(mean_returns)
    
    def portfolio_stats(weights):
        portfolio_return = np.sum(weights * mean_returns)
        portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_std
        return portfolio_return, portfolio_std, sharpe_ratio
    
    # Optimization constraints
    constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
    bounds = tuple((0, 1) for _ in range(n_assets))
    initial_weights = np.array([1/n_assets] * n_assets)
    
    if target_return:
        # Minimize risk for target return
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
            {'type': 'eq', 'fun': lambda x: portfolio_stats(x)[0] - target_return}
        ]
        result = optimize.minimize(
            lambda w: portfolio_stats(w)[1],
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
    else:
        # Maximize Sharpe ratio
        result = optimize.minimize(
            lambda w: -portfolio_stats(w)[2],
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
    
    optimal_weights = result.x
    ret, std, sharpe = portfolio_stats(optimal_weights)
    
    return {
        'weights': optimal_weights,
        'return': ret,
        'volatility': std,
        'sharpe_ratio': sharpe
    }


def calculate_var(
    returns: Union[pd.Series, np.ndarray],
    confidence_level: float = 0.95,
    time_horizon: int = 1,
    method: str = 'historical'
) -> Dict[str, float]:
    """
    Calculate Value at Risk (VaR)
    
    Args:
        returns: Historical returns
        confidence_level: Confidence level (e.g., 0.95 for 95%)
        time_horizon: Time horizon in days
        method: 'historical', 'parametric', or 'monte_carlo'
    
    Returns:
        VaR metrics
    """
    if isinstance(returns, pd.Series):
        returns = returns.values
    
    # Scale returns for time horizon
    scaled_returns = returns * np.sqrt(time_horizon)
    
    if method == 'historical':
        var = np.percentile(scaled_returns, (1 - confidence_level) * 100)
        cvar = scaled_returns[scaled_returns <= var].mean()
        
    elif method == 'parametric':
        mean = np.mean(scaled_returns)
        std = np.std(scaled_returns)
        z_score = stats.norm.ppf(1 - confidence_level)
        var = mean + z_score * std
        # Conditional VaR for normal distribution
        pdf_z = stats.norm.pdf(z_score)
        cvar = mean - std * pdf_z / (1 - confidence_level)
        
    elif method == 'monte_carlo':
        # Monte Carlo simulation
        mean = np.mean(returns)
        std = np.std(returns)
        simulations = np.random.normal(mean, std, (10000, time_horizon))
        portfolio_returns = np.prod(1 + simulations, axis=1) - 1
        var = np.percentile(portfolio_returns, (1 - confidence_level) * 100)
        cvar = portfolio_returns[portfolio_returns <= var].mean()
    
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return {
        'var': abs(var),
        'cvar': abs(cvar),
        'confidence_level': confidence_level,
        'time_horizon': time_horizon,
        'method': method
    }


def sharpe_ratio(
    returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252
) -> float:
    """
    Calculate Sharpe Ratio
    
    Args:
        returns: Return series
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods per year
    
    Returns:
        Annualized Sharpe ratio
    """
    if isinstance(returns, pd.Series):
        returns = returns.values
    
    excess_returns = returns - risk_free_rate / periods_per_year
    return np.sqrt(periods_per_year) * (excess_returns.mean() / excess_returns.std())


def sortino_ratio(
    returns: Union[pd.Series, np.ndarray],
    target_return: float = 0,
    periods_per_year: int = 252
) -> float:
    """
    Calculate Sortino Ratio (downside deviation)
    
    Args:
        returns: Return series
        target_return: Minimum acceptable return
        periods_per_year: Number of periods per year
    
    Returns:
        Annualized Sortino ratio
    """
    if isinstance(returns, pd.Series):
        returns = returns.values
    
    excess_returns = returns - target_return / periods_per_year
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0:
        return np.inf
    
    downside_deviation = np.std(downside_returns)
    return np.sqrt(periods_per_year) * (excess_returns.mean() / downside_deviation)


def maximum_drawdown(prices: Union[pd.Series, np.ndarray]) -> Dict[str, float]:
    """
    Calculate maximum drawdown and duration
    
    Args:
        prices: Price series
    
    Returns:
        Drawdown metrics
    """
    if isinstance(prices, np.ndarray):
        prices = pd.Series(prices)
    
    cumulative = prices / prices.iloc[0]
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    
    max_dd = drawdown.min()
    max_dd_idx = drawdown.idxmin()
    
    # Find drawdown start (peak before trough)
    peak_idx = cumulative[:max_dd_idx].idxmax()
    
    # Find recovery (if any)
    recovery_mask = cumulative[max_dd_idx:] >= cumulative[peak_idx]
    if recovery_mask.any():
        recovery_idx = cumulative[max_dd_idx:][recovery_mask].index[0]
        duration = (recovery_idx - peak_idx).days if hasattr(peak_idx, 'days') else recovery_idx - peak_idx
    else:
        duration = None
    
    return {
        'max_drawdown': abs(max_dd),
        'peak_date': peak_idx,
        'trough_date': max_dd_idx,
        'duration_days': duration
    }


# ==============================================================================
# Option Pricing
# ==============================================================================

def black_scholes(
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    option_type: str = 'call',
    dividend_yield: float = 0
) -> Dict[str, float]:
    """
    Black-Scholes option pricing with Greeks
    
    Args:
        spot: Current price of underlying
        strike: Strike price
        time_to_expiry: Time to expiration in years
        risk_free_rate: Risk-free interest rate
        volatility: Implied volatility
        option_type: 'call' or 'put'
        dividend_yield: Continuous dividend yield
    
    Returns:
        Option price and Greeks
    """
    # Adjust for dividends
    spot_adj = spot * np.exp(-dividend_yield * time_to_expiry)
    
    # Calculate d1 and d2
    d1 = (np.log(spot_adj / strike) + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / \
         (volatility * np.sqrt(time_to_expiry))
    d2 = d1 - volatility * np.sqrt(time_to_expiry)
    
    # Option price
    if option_type.lower() == 'call':
        price = spot_adj * stats.norm.cdf(d1) - strike * np.exp(-risk_free_rate * time_to_expiry) * stats.norm.cdf(d2)
        delta = np.exp(-dividend_yield * time_to_expiry) * stats.norm.cdf(d1)
        theta = (-spot * stats.norm.pdf(d1) * volatility * np.exp(-dividend_yield * time_to_expiry) / 
                (2 * np.sqrt(time_to_expiry)) - risk_free_rate * strike * np.exp(-risk_free_rate * time_to_expiry) * 
                stats.norm.cdf(d2) + dividend_yield * spot * np.exp(-dividend_yield * time_to_expiry) * stats.norm.cdf(d1))
    else:  # put
        price = strike * np.exp(-risk_free_rate * time_to_expiry) * stats.norm.cdf(-d2) - spot_adj * stats.norm.cdf(-d1)
        delta = -np.exp(-dividend_yield * time_to_expiry) * stats.norm.cdf(-d1)
        theta = (-spot * stats.norm.pdf(d1) * volatility * np.exp(-dividend_yield * time_to_expiry) / 
                (2 * np.sqrt(time_to_expiry)) + risk_free_rate * strike * np.exp(-risk_free_rate * time_to_expiry) * 
                stats.norm.cdf(-d2) - dividend_yield * spot * np.exp(-dividend_yield * time_to_expiry) * stats.norm.cdf(-d1))
    
    # Common Greeks
    gamma = stats.norm.pdf(d1) * np.exp(-dividend_yield * time_to_expiry) / (spot * volatility * np.sqrt(time_to_expiry))
    vega = spot * stats.norm.pdf(d1) * np.sqrt(time_to_expiry) * np.exp(-dividend_yield * time_to_expiry) / 100
    rho = strike * time_to_expiry * np.exp(-risk_free_rate * time_to_expiry) * \
          (stats.norm.cdf(d2) if option_type.lower() == 'call' else -stats.norm.cdf(-d2)) / 100
    
    return {
        'price': price,
        'delta': delta,
        'gamma': gamma,
        'theta': theta / 365,  # Convert to daily theta
        'vega': vega,
        'rho': rho,
        'intrinsic_value': max(0, spot - strike if option_type.lower() == 'call' else strike - spot),
        'time_value': price - max(0, spot - strike if option_type.lower() == 'call' else strike - spot)
    }


def implied_volatility(
    option_price: float,
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    option_type: str = 'call',
    dividend_yield: float = 0
) -> float:
    """
    Calculate implied volatility using Newton-Raphson method
    
    Args:
        option_price: Market price of option
        spot: Current price of underlying
        strike: Strike price
        time_to_expiry: Time to expiration in years
        risk_free_rate: Risk-free interest rate
        option_type: 'call' or 'put'
        dividend_yield: Continuous dividend yield
    
    Returns:
        Implied volatility
    """
    def objective(vol):
        theoretical = black_scholes(spot, strike, time_to_expiry, risk_free_rate, 
                                   vol, option_type, dividend_yield)['price']
        return theoretical - option_price
    
    try:
        # Use Brent's method for robust convergence
        iv = optimize.brentq(objective, 0.001, 5.0)
        return iv
    except:
        # Fallback to initial guess if no solution found
        return 0.2


# ==============================================================================
# Fixed Income Analytics
# ==============================================================================

def bond_price(
    face_value: float,
    coupon_rate: float,
    yield_to_maturity: float,
    years_to_maturity: float,
    frequency: int = 2
) -> float:
    """
    Calculate bond price
    
    Args:
        face_value: Par value of bond
        coupon_rate: Annual coupon rate
        yield_to_maturity: Annual YTM
        years_to_maturity: Time to maturity in years
        frequency: Coupon payment frequency per year
    
    Returns:
        Bond price
    """
    periods = int(years_to_maturity * frequency)
    coupon_payment = face_value * coupon_rate / frequency
    discount_rate = yield_to_maturity / frequency
    
    # Present value of coupons
    pv_coupons = sum([coupon_payment / (1 + discount_rate) ** i 
                     for i in range(1, periods + 1)])
    
    # Present value of face value
    pv_face = face_value / (1 + discount_rate) ** periods
    
    return pv_coupons + pv_face


def bond_duration(
    face_value: float,
    coupon_rate: float,
    yield_to_maturity: float,
    years_to_maturity: float,
    frequency: int = 2
) -> Dict[str, float]:
    """
    Calculate bond duration and convexity
    
    Args:
        face_value: Par value of bond
        coupon_rate: Annual coupon rate
        yield_to_maturity: Annual YTM
        years_to_maturity: Time to maturity in years
        frequency: Coupon payment frequency per year
    
    Returns:
        Duration and convexity metrics
    """
    periods = int(years_to_maturity * frequency)
    coupon_payment = face_value * coupon_rate / frequency
    discount_rate = yield_to_maturity / frequency
    
    # Calculate price
    price = bond_price(face_value, coupon_rate, yield_to_maturity, years_to_maturity, frequency)
    
    # Macaulay duration
    weighted_pv = sum([t * coupon_payment / (1 + discount_rate) ** t 
                      for t in range(1, periods + 1)])
    weighted_pv += periods * face_value / (1 + discount_rate) ** periods
    macaulay_duration = weighted_pv / price / frequency
    
    # Modified duration
    modified_duration = macaulay_duration / (1 + yield_to_maturity / frequency)
    
    # Convexity
    convexity = sum([t * (t + 1) * coupon_payment / (1 + discount_rate) ** (t + 2) 
                    for t in range(1, periods + 1)])
    convexity += periods * (periods + 1) * face_value / (1 + discount_rate) ** (periods + 2)
    convexity = convexity / price / frequency ** 2
    
    return {
        'price': price,
        'macaulay_duration': macaulay_duration,
        'modified_duration': modified_duration,
        'convexity': convexity,
        'dv01': price * modified_duration * 0.0001  # Dollar value of 1 basis point
    }


# ==============================================================================
# Financial Ratios
# ==============================================================================

@dataclass
class FinancialRatios:
    """Calculate comprehensive financial ratios"""
    
    # Income Statement items
    revenue: float
    gross_profit: float
    operating_income: float
    net_income: float
    ebitda: float
    interest_expense: float
    
    # Balance Sheet items
    total_assets: float
    current_assets: float
    current_liabilities: float
    total_debt: float
    total_equity: float
    inventory: float
    receivables: float
    cash: float
    
    # Other items
    shares_outstanding: float
    stock_price: float
    dividends_paid: float
    
    @property
    def profitability_ratios(self) -> Dict[str, float]:
        """Calculate profitability ratios"""
        return {
            'gross_margin': self.gross_profit / self.revenue,
            'operating_margin': self.operating_income / self.revenue,
            'net_margin': self.net_income / self.revenue,
            'roe': self.net_income / self.total_equity,
            'roa': self.net_income / self.total_assets,
            'roce': self.operating_income / (self.total_assets - self.current_liabilities)
        }
    
    @property
    def liquidity_ratios(self) -> Dict[str, float]:
        """Calculate liquidity ratios"""
        return {
            'current_ratio': self.current_assets / self.current_liabilities,
            'quick_ratio': (self.current_assets - self.inventory) / self.current_liabilities,
            'cash_ratio': self.cash / self.current_liabilities
        }
    
    @property
    def leverage_ratios(self) -> Dict[str, float]:
        """Calculate leverage ratios"""
        return {
            'debt_to_equity': self.total_debt / self.total_equity,
            'debt_to_assets': self.total_debt / self.total_assets,
            'interest_coverage': self.ebitda / self.interest_expense if self.interest_expense > 0 else np.inf,
            'debt_to_ebitda': self.total_debt / self.ebitda if self.ebitda > 0 else np.inf
        }
    
    @property
    def valuation_ratios(self) -> Dict[str, float]:
        """Calculate valuation ratios"""
        market_cap = self.stock_price * self.shares_outstanding
        enterprise_value = market_cap + self.total_debt - self.cash
        
        return {
            'pe_ratio': market_cap / self.net_income if self.net_income > 0 else np.inf,
            'price_to_book': market_cap / self.total_equity,
            'ev_to_ebitda': enterprise_value / self.ebitda if self.ebitda > 0 else np.inf,
            'ev_to_revenue': enterprise_value / self.revenue,
            'dividend_yield': self.dividends_paid / market_cap
        }
    
    @property
    def efficiency_ratios(self) -> Dict[str, float]:
        """Calculate efficiency ratios"""
        return {
            'asset_turnover': self.revenue / self.total_assets,
            'receivables_turnover': self.revenue / self.receivables if self.receivables > 0 else np.inf,
            'inventory_turnover': self.revenue / self.inventory if self.inventory > 0 else np.inf,
            'days_receivables': 365 * self.receivables / self.revenue,
            'days_inventory': 365 * self.inventory / self.revenue
        }


# ==============================================================================
# Energy Finance Calculations
# ==============================================================================

def project_finance_model(
    capex: float,
    annual_revenue: List[float],
    annual_opex: List[float],
    debt_ratio: float,
    interest_rate: float,
    loan_term: int,
    tax_rate: float,
    discount_rate: float
) -> Dict[str, Union[float, pd.DataFrame]]:
    """
    Energy project finance model
    
    Args:
        capex: Capital expenditure
        annual_revenue: List of annual revenues
        annual_opex: List of annual operating expenses
        debt_ratio: Debt to total capital ratio
        interest_rate: Interest rate on debt
        loan_term: Loan term in years
        tax_rate: Corporate tax rate
        discount_rate: Project discount rate
    
    Returns:
        Project metrics and cash flow table
    """
    # Financing structure
    debt_amount = capex * debt_ratio
    equity_amount = capex * (1 - debt_ratio)
    
    # Debt schedule
    annual_debt_service = debt_amount * (interest_rate * (1 + interest_rate) ** loan_term) / \
                         ((1 + interest_rate) ** loan_term - 1)
    
    # Cash flow projections
    years = len(annual_revenue)
    cash_flows = []
    
    for year in range(years):
        revenue = annual_revenue[year]
        opex = annual_opex[year]
        
        # Interest expense (declining as principal is paid)
        if year < loan_term:
            principal_remaining = debt_amount * (1 - year / loan_term)  # Simplified
            interest_expense = principal_remaining * interest_rate
            principal_payment = annual_debt_service - interest_expense
        else:
            interest_expense = 0
            principal_payment = 0
        
        # EBITDA and tax
        ebitda = revenue - opex
        ebt = ebitda - interest_expense
        tax = max(0, ebt * tax_rate)
        net_income = ebt - tax
        
        # Free cash flow
        fcf = net_income + interest_expense * (1 - tax_rate) - principal_payment
        
        cash_flows.append({
            'year': year + 1,
            'revenue': revenue,
            'opex': opex,
            'ebitda': ebitda,
            'interest': interest_expense,
            'tax': tax,
            'net_income': net_income,
            'fcf': fcf,
            'debt_service': annual_debt_service if year < loan_term else 0
        })
    
    # Create DataFrame
    cf_df = pd.DataFrame(cash_flows)
    
    # Calculate metrics
    project_npv = -capex + sum([cf['fcf'] / (1 + discount_rate) ** cf['year'] 
                               for cf in cash_flows])
    
    # IRR calculation
    irr_cash_flows = [-capex] + [cf['fcf'] for cf in cash_flows]
    try:
        project_irr = np.irr(irr_cash_flows)
    except:
        project_irr = None
    
    # DSCR (Debt Service Coverage Ratio)
    dscr_values = []
    for year in range(min(loan_term, years)):
        if cash_flows[year]['debt_service'] > 0:
            dscr = cash_flows[year]['ebitda'] / cash_flows[year]['debt_service']
            dscr_values.append(dscr)
    
    min_dscr = min(dscr_values) if dscr_values else None
    avg_dscr = np.mean(dscr_values) if dscr_values else None
    
    return {
        'npv': project_npv,
        'irr': project_irr,
        'equity_irr': None,  # Would need more detailed calc
        'min_dscr': min_dscr,
        'avg_dscr': avg_dscr,
        'payback_period': None,  # Would need cumulative cash flow calc
        'cash_flows': cf_df
    }


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Example: DCF Valuation
    fcf = [100, 110, 121, 133, 146]  # Million USD
    valuation = dcf_valuation(fcf, 0.03, 0.10)
    print(f"Enterprise Value: ${valuation['enterprise_value']:,.2f}M")
    
    # Example: Portfolio Optimization
    returns_data = pd.DataFrame({
        'Stock_A': np.random.normal(0.001, 0.02, 252),
        'Stock_B': np.random.normal(0.0008, 0.015, 252),
        'Stock_C': np.random.normal(0.0012, 0.025, 252)
    })
    
    optimal_portfolio = portfolio_optimization(returns_data)
    print(f"Optimal Weights: {optimal_portfolio['weights']}")
    print(f"Expected Return: {optimal_portfolio['return']:.2%}")
    print(f"Sharpe Ratio: {optimal_portfolio['sharpe_ratio']:.2f}")
    
    # Example: Option Pricing
    option = black_scholes(
        spot=100,
        strike=105,
        time_to_expiry=0.25,
        risk_free_rate=0.05,
        volatility=0.2,
        option_type='call'
    )
    print(f"Call Option Price: ${option['price']:.2f}")
    print(f"Delta: {option['delta']:.3f}")
    
    # Example: VaR Calculation
    var_metrics = calculate_var(returns_data['Stock_A'], confidence_level=0.95, method='historical')
    print(f"95% VaR: {var_metrics['var']:.2%}")
    print(f"CVaR: {var_metrics['cvar']:.2%}")