---
name: production-forecaster
description: Forecast oil & gas well production using decline curve analysis. Use for EUR estimation, type curve generation, production modeling, and reserve calculations with Arps decline models (exponential, hyperbolic, harmonic).
version: 1.0.0
last_updated: 2025-12-30
---

# Production Forecaster

Forecast oil and gas production using industry-standard decline curve analysis methods. Supports Arps decline models, type curve generation, and EUR (Estimated Ultimate Recovery) calculations for reserve estimation.

## When to Use

- Forecasting future production for oil and gas wells
- Estimating EUR (Estimated Ultimate Recovery)
- Generating type curves for field development planning
- Fitting decline parameters to historical production data
- Comparing well performance across different fields
- Supporting reserve booking and economic evaluation
- Analyzing production trends and anomalies

## Core Pattern

```
Historical Production → Decline Curve Fit → Parameter Estimation → Forecast → EUR
```

## Decline Curve Models

### Arps Decline Equations

**Exponential Decline (b = 0):**
```
q(t) = qi * exp(-Di * t)
```

**Hyperbolic Decline (0 < b < 1):**
```
q(t) = qi / (1 + b * Di * t)^(1/b)
```

**Harmonic Decline (b = 1):**
```
q(t) = qi / (1 + Di * t)
```

Where:
- `q(t)` = Production rate at time t
- `qi` = Initial production rate
- `Di` = Initial decline rate
- `b` = Decline exponent (b-factor)
- `t` = Time

## Implementation

### Data Models

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Dict, Tuple
from enum import Enum
import numpy as np
import pandas as pd

class DeclineType(Enum):
    """Arps decline curve types."""
    EXPONENTIAL = "exponential"  # b = 0
    HYPERBOLIC = "hyperbolic"    # 0 < b < 1
    HARMONIC = "harmonic"        # b = 1

class ProductionPhase(Enum):
    """Well production phases."""
    BUILDUP = "buildup"
    PLATEAU = "plateau"
    DECLINE = "decline"
    ABANDONMENT = "abandonment"

@dataclass
class DeclineParameters:
    """Decline curve parameters."""
    qi: float  # Initial rate (bbls/day or mcf/day)
    di: float  # Initial decline rate (fraction/year)
    b: float   # Decline exponent
    decline_type: DeclineType = DeclineType.HYPERBOLIC

    # Optional constraints
    min_rate: float = 0.0  # Economic limit
    max_time: float = 50.0  # Years
    d_min: Optional[float] = None  # Terminal decline rate

    def __post_init__(self):
        """Validate parameters and set decline type."""
        if self.b == 0:
            self.decline_type = DeclineType.EXPONENTIAL
        elif self.b == 1:
            self.decline_type = DeclineType.HARMONIC
        else:
            self.decline_type = DeclineType.HYPERBOLIC

@dataclass
class ProductionRecord:
    """Single production record."""
    date: date
    oil_rate: float = 0.0      # bbls/day
    gas_rate: float = 0.0      # mcf/day
    water_rate: float = 0.0    # bbls/day
    days_on: int = 30          # Days producing

    @property
    def oil_volume(self) -> float:
        """Monthly oil volume in barrels."""
        return self.oil_rate * self.days_on

    @property
    def gas_volume(self) -> float:
        """Monthly gas volume in mcf."""
        return self.gas_rate * self.days_on

    @property
    def gor(self) -> float:
        """Gas-oil ratio (mcf/bbl)."""
        if self.oil_rate > 0:
            return self.gas_rate / self.oil_rate
        return 0.0

@dataclass
class ForecastResult:
    """Production forecast results."""
    dates: List[date]
    oil_rates: List[float]
    gas_rates: List[float]
    cumulative_oil: List[float]
    cumulative_gas: List[float]

    # Decline parameters used
    parameters: DeclineParameters

    # Key metrics
    eur_oil: float = 0.0       # Estimated Ultimate Recovery (bbls)
    eur_gas: float = 0.0       # EUR gas (mcf)
    remaining_oil: float = 0.0  # Remaining reserves
    remaining_gas: float = 0.0

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame."""
        return pd.DataFrame({
            'date': self.dates,
            'oil_rate': self.oil_rates,
            'gas_rate': self.gas_rates,
            'cumulative_oil': self.cumulative_oil,
            'cumulative_gas': self.cumulative_gas
        })
```

### Decline Curve Analyzer

```python
import numpy as np
from scipy.optimize import curve_fit, minimize
from typing import Tuple, Optional
import pandas as pd

class DeclineCurveAnalyzer:
    """
    Analyze and fit decline curves to production data.
    """

    def __init__(self, production_data: pd.DataFrame):
        """
        Initialize with production data.

        Args:
            production_data: DataFrame with 'date' and 'rate' columns
        """
        self.data = production_data.copy()
        self._prepare_data()

    def _prepare_data(self):
        """Prepare data for analysis."""
        self.data['date'] = pd.to_datetime(self.data['date'])
        self.data = self.data.sort_values('date')

        # Calculate time from first production
        first_date = self.data['date'].min()
        self.data['time_years'] = (
            (self.data['date'] - first_date).dt.days / 365.25
        )

    @staticmethod
    def exponential_decline(t: np.ndarray, qi: float, di: float) -> np.ndarray:
        """Exponential decline model."""
        return qi * np.exp(-di * t)

    @staticmethod
    def hyperbolic_decline(t: np.ndarray, qi: float, di: float,
                          b: float) -> np.ndarray:
        """Hyperbolic decline model."""
        return qi / np.power(1 + b * di * t, 1/b)

    @staticmethod
    def harmonic_decline(t: np.ndarray, qi: float, di: float) -> np.ndarray:
        """Harmonic decline model."""
        return qi / (1 + di * t)

    def fit_exponential(self) -> DeclineParameters:
        """Fit exponential decline curve."""
        t = self.data['time_years'].values
        q = self.data['rate'].values

        # Initial guesses
        qi_guess = q[0]
        di_guess = 0.3

        try:
            popt, _ = curve_fit(
                self.exponential_decline,
                t, q,
                p0=[qi_guess, di_guess],
                bounds=([0, 0], [qi_guess * 2, 2.0]),
                maxfev=5000
            )
            return DeclineParameters(qi=popt[0], di=popt[1], b=0.0)
        except:
            return DeclineParameters(qi=qi_guess, di=di_guess, b=0.0)

    def fit_hyperbolic(self, b_range: Tuple[float, float] = (0.1, 0.9)
                      ) -> DeclineParameters:
        """Fit hyperbolic decline curve."""
        t = self.data['time_years'].values
        q = self.data['rate'].values

        # Initial guesses
        qi_guess = q[0]
        di_guess = 0.3
        b_guess = 0.5

        try:
            popt, _ = curve_fit(
                self.hyperbolic_decline,
                t, q,
                p0=[qi_guess, di_guess, b_guess],
                bounds=(
                    [0, 0, b_range[0]],
                    [qi_guess * 2, 2.0, b_range[1]]
                ),
                maxfev=5000
            )
            return DeclineParameters(qi=popt[0], di=popt[1], b=popt[2])
        except:
            return DeclineParameters(qi=qi_guess, di=di_guess, b=b_guess)

    def fit_best_model(self) -> Tuple[DeclineParameters, str]:
        """
        Fit all models and return best fit.

        Returns:
            Tuple of (best parameters, model name)
        """
        models = {
            'exponential': self.fit_exponential(),
            'hyperbolic': self.fit_hyperbolic(),
        }

        t = self.data['time_years'].values
        q = self.data['rate'].values

        best_model = None
        best_rmse = float('inf')
        best_params = None

        for name, params in models.items():
            if name == 'exponential':
                predicted = self.exponential_decline(t, params.qi, params.di)
            else:
                predicted = self.hyperbolic_decline(
                    t, params.qi, params.di, params.b
                )

            rmse = np.sqrt(np.mean((q - predicted) ** 2))

            if rmse < best_rmse:
                best_rmse = rmse
                best_model = name
                best_params = params

        return best_params, best_model

    def calculate_eur(self, params: DeclineParameters,
                     economic_limit: float = 10.0,
                     max_years: float = 50.0) -> float:
        """
        Calculate Estimated Ultimate Recovery.

        Args:
            params: Decline parameters
            economic_limit: Minimum economic rate
            max_years: Maximum forecast period
        """
        if params.b == 0:
            # Exponential: EUR with economic limit and time cap
            # Time to reach economic limit: t = ln(qi/q_limit) / di
            t_econ = np.log(params.qi / economic_limit) / params.di
            t_max = min(max_years, t_econ)
            # Cumulative: Np = (qi/di) * (1 - exp(-di*t))
            return params.qi * 365.25 / params.di * (1 - np.exp(-params.di * t_max))
        elif params.b == 1:
            # Harmonic: EUR is infinite, use time limit
            # Cumulative = qi/di * ln(1 + di*t)
            t_max = min(max_years, (params.qi / economic_limit - 1) / params.di)
            return params.qi * 365.25 / params.di * np.log(1 + params.di * t_max)
        else:
            # Hyperbolic
            # Cumulative = qi^b / (di * (1-b)) * (qi^(1-b) - q_limit^(1-b))
            q_limit = max(economic_limit, 0.1)
            factor = params.qi ** params.b / (params.di * (1 - params.b))
            cum = factor * (params.qi ** (1 - params.b) - q_limit ** (1 - params.b))
            return cum * 365.25
```

### Production Forecaster

```python
from datetime import date, timedelta
from typing import List, Optional
import numpy as np
import pandas as pd

class ProductionForecaster:
    """
    Generate production forecasts using decline curve analysis.
    """

    def __init__(self, parameters: DeclineParameters,
                 start_date: date = None,
                 cumulative_to_date: float = 0.0):
        """
        Initialize forecaster.

        Args:
            parameters: Decline curve parameters
            start_date: Forecast start date
            cumulative_to_date: Production already recovered
        """
        self.params = parameters
        self.start_date = start_date or date.today()
        self.cum_to_date = cumulative_to_date

    def _calculate_rate(self, t: float) -> float:
        """Calculate rate at time t (years)."""
        if self.params.b == 0:
            return self.params.qi * np.exp(-self.params.di * t)
        elif self.params.b == 1:
            return self.params.qi / (1 + self.params.di * t)
        else:
            return self.params.qi / np.power(
                1 + self.params.b * self.params.di * t,
                1 / self.params.b
            )

    def _calculate_cumulative(self, t: float) -> float:
        """Calculate cumulative production at time t (years)."""
        if self.params.b == 0:
            # Exponential
            return self.params.qi / self.params.di * (
                1 - np.exp(-self.params.di * t)
            ) * 365.25
        elif self.params.b == 1:
            # Harmonic
            return self.params.qi / self.params.di * np.log(
                1 + self.params.di * t
            ) * 365.25
        else:
            # Hyperbolic
            q_t = self._calculate_rate(t)
            factor = self.params.qi ** self.params.b / (
                self.params.di * (1 - self.params.b)
            )
            return factor * (
                self.params.qi ** (1 - self.params.b) -
                q_t ** (1 - self.params.b)
            ) * 365.25

    def forecast(self, years: float = 30.0,
                interval_months: int = 1,
                economic_limit: float = 10.0,
                gor: float = 1.0) -> ForecastResult:
        """
        Generate production forecast.

        Args:
            years: Forecast period in years
            interval_months: Output interval in months
            economic_limit: Minimum economic rate (bbls/day or mcf/day)
            gor: Gas-oil ratio for gas calculation

        Returns:
            ForecastResult with forecast data
        """
        dates = []
        oil_rates = []
        gas_rates = []
        cumulative_oil = []
        cumulative_gas = []

        current_date = self.start_date
        total_months = int(years * 12)

        for month in range(0, total_months, interval_months):
            t = month / 12.0  # Time in years

            rate = self._calculate_rate(t)

            # Check economic limit
            if rate < economic_limit:
                break

            cum = self._calculate_cumulative(t) + self.cum_to_date

            dates.append(current_date)
            oil_rates.append(rate)
            gas_rates.append(rate * gor)
            cumulative_oil.append(cum)
            cumulative_gas.append(cum * gor)

            # Advance date by interval_months
            new_month = current_date.month + interval_months
            new_year = current_date.year + (new_month - 1) // 12
            new_month = ((new_month - 1) % 12) + 1
            current_date = date(new_year, new_month, 1)

        # Calculate EUR
        analyzer = DeclineCurveAnalyzer.__new__(DeclineCurveAnalyzer)
        eur_oil = analyzer.calculate_eur(
            self.params, economic_limit, years
        ) + self.cum_to_date

        return ForecastResult(
            dates=dates,
            oil_rates=oil_rates,
            gas_rates=gas_rates,
            cumulative_oil=cumulative_oil,
            cumulative_gas=cumulative_gas,
            parameters=self.params,
            eur_oil=eur_oil,
            eur_gas=eur_oil * gor,
            remaining_oil=eur_oil - self.cum_to_date,
            remaining_gas=(eur_oil - self.cum_to_date) * gor
        )

    def to_dataframe(self, forecast: ForecastResult) -> pd.DataFrame:
        """Convert forecast to DataFrame."""
        return forecast.to_dataframe()
```

### Type Curve Generator

```python
from typing import List, Dict, Optional
import numpy as np
import pandas as pd

class TypeCurveGenerator:
    """
    Generate type curves from multiple well production histories.
    """

    def __init__(self, wells: List[pd.DataFrame]):
        """
        Initialize with list of well production DataFrames.

        Args:
            wells: List of DataFrames with 'date' and 'rate' columns
        """
        self.wells = wells
        self.normalized_wells = []

    def normalize_wells(self, normalize_to: str = 'peak') -> List[pd.DataFrame]:
        """
        Normalize wells for type curve generation.

        Args:
            normalize_to: 'peak' or 'first_month'
        """
        normalized = []

        for well in self.wells:
            df = well.copy()
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')

            # Calculate months from start
            first_date = df['date'].min()
            df['month'] = ((df['date'] - first_date).dt.days / 30.44).astype(int)

            # Normalize rate
            if normalize_to == 'peak':
                peak_rate = df['rate'].max()
            else:
                peak_rate = df['rate'].iloc[0]

            df['normalized_rate'] = df['rate'] / peak_rate

            normalized.append(df)

        self.normalized_wells = normalized
        return normalized

    def generate_type_curve(self,
                           percentiles: List[float] = [10, 50, 90]
                           ) -> pd.DataFrame:
        """
        Generate type curve with percentile ranges.

        Args:
            percentiles: Percentiles to calculate (P10, P50, P90)

        Returns:
            DataFrame with type curves
        """
        if not self.normalized_wells:
            self.normalize_wells()

        # Find maximum months across all wells
        max_months = max(df['month'].max() for df in self.normalized_wells)

        # Collect rates by month
        monthly_rates = {m: [] for m in range(int(max_months) + 1)}

        for df in self.normalized_wells:
            for _, row in df.iterrows():
                month = int(row['month'])
                if month in monthly_rates:
                    monthly_rates[month].append(row['normalized_rate'])

        # Calculate percentiles
        type_curve_data = []
        for month in sorted(monthly_rates.keys()):
            rates = monthly_rates[month]
            if len(rates) >= 3:  # Need minimum wells
                row = {'month': month}
                for p in percentiles:
                    row[f'P{p}'] = np.percentile(rates, 100 - p)
                row['mean'] = np.mean(rates)
                row['well_count'] = len(rates)
                type_curve_data.append(row)

        return pd.DataFrame(type_curve_data)

    def fit_type_curve(self, percentile: float = 50) -> DeclineParameters:
        """
        Fit decline curve to type curve percentile.

        Args:
            percentile: Percentile to fit (e.g., 50 for P50)
        """
        type_curve = self.generate_type_curve([percentile])

        # Create analyzer with type curve data
        tc_df = pd.DataFrame({
            'date': pd.date_range(start='2020-01-01', periods=len(type_curve), freq='MS'),
            'rate': type_curve[f'P{percentile}'].values
        })

        analyzer = DeclineCurveAnalyzer(tc_df)
        params, _ = analyzer.fit_best_model()

        return params
```

### Report Generator

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import pandas as pd

class ProductionReportGenerator:
    """Generate interactive HTML reports for production forecasts."""

    def __init__(self, forecast: ForecastResult,
                 historical_data: pd.DataFrame = None):
        """
        Initialize report generator.

        Args:
            forecast: Forecast results
            historical_data: Optional historical production data
        """
        self.forecast = forecast
        self.historical = historical_data

    def generate_report(self, output_path: Path,
                       well_name: str = "Well") -> Path:
        """Generate comprehensive production forecast report."""

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Production Rate Forecast',
                'Cumulative Production',
                'Decline Curve Analysis',
                'Forecast Summary'
            ),
            specs=[
                [{'type': 'scatter'}, {'type': 'scatter'}],
                [{'type': 'scatter'}, {'type': 'table'}]
            ]
        )

        forecast_df = self.forecast.to_dataframe()

        # Production Rate Plot
        if self.historical is not None:
            fig.add_trace(
                go.Scatter(
                    x=self.historical['date'],
                    y=self.historical['rate'],
                    mode='markers',
                    name='Historical',
                    marker=dict(color='blue', size=6)
                ),
                row=1, col=1
            )

        fig.add_trace(
            go.Scatter(
                x=forecast_df['date'],
                y=forecast_df['oil_rate'],
                mode='lines',
                name='Forecast',
                line=dict(color='red', width=2)
            ),
            row=1, col=1
        )

        # Cumulative Production
        fig.add_trace(
            go.Scatter(
                x=forecast_df['date'],
                y=forecast_df['cumulative_oil'],
                fill='tozeroy',
                name='Cumulative Oil',
                line=dict(color='green')
            ),
            row=1, col=2
        )

        # Add EUR line
        fig.add_hline(
            y=self.forecast.eur_oil,
            line_dash='dash',
            line_color='orange',
            annotation_text=f'EUR: {self.forecast.eur_oil/1e6:.2f} MMbbls',
            row=1, col=2
        )

        # Decline Curve (semi-log)
        fig.add_trace(
            go.Scatter(
                x=forecast_df['date'],
                y=forecast_df['oil_rate'],
                mode='lines',
                name='Rate (log)',
                line=dict(color='purple')
            ),
            row=2, col=1
        )
        fig.update_yaxes(type='log', row=2, col=1)

        # Summary Table
        params = self.forecast.parameters
        summary_data = {
            'Parameter': [
                'Initial Rate (qi)',
                'Decline Rate (Di)',
                'b-factor',
                'Decline Type',
                'EUR Oil',
                'EUR Gas',
                'Remaining Oil',
                'Remaining Gas'
            ],
            'Value': [
                f'{params.qi:.1f} bbl/d',
                f'{params.di*100:.1f} %/year',
                f'{params.b:.3f}',
                params.decline_type.value,
                f'{self.forecast.eur_oil/1e6:.2f} MMbbl',
                f'{self.forecast.eur_gas/1e6:.2f} MMmcf',
                f'{self.forecast.remaining_oil/1e6:.2f} MMbbl',
                f'{self.forecast.remaining_gas/1e6:.2f} MMmcf'
            ]
        }

        fig.add_trace(
            go.Table(
                header=dict(
                    values=['Parameter', 'Value'],
                    fill_color='paleturquoise',
                    align='left'
                ),
                cells=dict(
                    values=[summary_data['Parameter'], summary_data['Value']],
                    fill_color='lavender',
                    align='left'
                )
            ),
            row=2, col=2
        )

        fig.update_layout(
            height=800,
            title_text=f'{well_name} - Production Forecast',
            showlegend=True
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_path))

        return output_path
```

## YAML Configuration

### Forecast Configuration

```yaml
# config/production_forecast.yaml

metadata:
  well_name: "Well A-1"
  field: "Deepwater GOM"
  analyst: "Engineering Team"
  date: "2025-01-15"

historical_data:
  source: "file"
  file_path: "data/production/well_a1_history.csv"
  date_column: "date"
  rate_column: "oil_rate"

decline_parameters:
  # Auto-fit from historical data
  auto_fit: true

  # Or manual parameters
  # qi: 5000  # Initial rate (bbl/day)
  # di: 0.35  # Initial decline (fraction/year)
  # b: 0.8    # Decline exponent

  # Constraints
  b_range: [0.3, 1.2]  # Typical for unconventional

forecast:
  start_date: "2025-01-01"
  years: 30
  economic_limit: 25  # bbl/day
  interval: "monthly"

gas:
  gor: 2.5  # mcf/bbl
  gor_trend: "constant"  # or "increasing", "decreasing"

output:
  csv_path: "data/results/well_a1_forecast.csv"
  report_path: "reports/well_a1_forecast.html"
```

### Type Curve Configuration

```yaml
# config/type_curve.yaml

metadata:
  field: "Lower Tertiary"
  formation: "Wilcox"
  analyst: "Reservoir Team"

wells:
  source: "directory"
  path: "data/production/lower_tertiary/"
  pattern: "*.csv"

  # Or explicit list
  # files:
  #   - "well_1.csv"
  #   - "well_2.csv"

normalization:
  method: "peak"  # or "first_month", "30_day_ip"

type_curve:
  percentiles: [10, 50, 90]
  min_wells_per_month: 5

fit:
  model: "hyperbolic"
  b_range: [0.5, 1.5]

output:
  type_curve_csv: "data/results/lower_tertiary_type_curve.csv"
  report_path: "reports/lower_tertiary_type_curves.html"
```

## CLI Usage

```bash
# Fit decline curve to historical data
python -m production_forecaster fit \
    --data data/production/well_history.csv \
    --model hyperbolic

# Generate forecast
python -m production_forecaster forecast \
    --config config/production_forecast.yaml \
    --output reports/forecast.html

# Generate type curves
python -m production_forecaster type-curve \
    --wells data/production/*.csv \
    --percentiles 10 50 90 \
    --output reports/type_curves.html

# Calculate EUR
python -m production_forecaster eur \
    --qi 5000 --di 0.35 --b 0.8 \
    --limit 25

# Compare wells
python -m production_forecaster compare \
    --wells well1.csv well2.csv well3.csv \
    --normalize peak \
    --output reports/comparison.html
```

## Usage Examples

### Example 1: Fit and Forecast Single Well

```python
from production_forecaster import (
    DeclineCurveAnalyzer, ProductionForecaster,
    ProductionReportGenerator
)
import pandas as pd
from pathlib import Path

# Load historical production
historical = pd.read_csv('data/production/well_a1.csv')

# Fit decline curve
analyzer = DeclineCurveAnalyzer(historical)
params, model_type = analyzer.fit_best_model()

print(f"Best fit: {model_type}")
print(f"qi = {params.qi:.1f} bbl/d")
print(f"Di = {params.di*100:.1f} %/year")
print(f"b = {params.b:.3f}")

# Generate forecast
forecaster = ProductionForecaster(
    params,
    cumulative_to_date=historical['cumulative'].iloc[-1]
)
forecast = forecaster.forecast(years=30, economic_limit=25)

print(f"\nEUR: {forecast.eur_oil/1e6:.2f} MMbbl")
print(f"Remaining: {forecast.remaining_oil/1e6:.2f} MMbbl")

# Generate report
reporter = ProductionReportGenerator(forecast, historical)
reporter.generate_report(
    Path('reports/well_a1_forecast.html'),
    well_name='Well A-1'
)
```

### Example 2: Generate Type Curves

```python
from production_forecaster import TypeCurveGenerator
import glob
import pandas as pd

# Load all well data
well_files = glob.glob('data/production/field_x/*.csv')
wells = [pd.read_csv(f) for f in well_files]

# Generate type curves
generator = TypeCurveGenerator(wells)
type_curve = generator.generate_type_curve(percentiles=[10, 50, 90])

print("Type Curve (first 12 months):")
print(type_curve.head(12))

# Fit P50 type curve
p50_params = generator.fit_type_curve(percentile=50)
print(f"\nP50 Type Curve Parameters:")
print(f"qi = {p50_params.qi:.3f} (normalized)")
print(f"Di = {p50_params.di*100:.1f} %/year")
print(f"b = {p50_params.b:.3f}")
```

### Example 3: Multi-Well Comparison

```python
from production_forecaster import DeclineCurveAnalyzer, ProductionForecaster
import pandas as pd
import plotly.graph_objects as go

wells = ['well_a.csv', 'well_b.csv', 'well_c.csv']
results = []

for well_file in wells:
    df = pd.read_csv(f'data/production/{well_file}')

    analyzer = DeclineCurveAnalyzer(df)
    params, _ = analyzer.fit_best_model()

    forecaster = ProductionForecaster(params)
    forecast = forecaster.forecast(years=20)

    results.append({
        'well': well_file,
        'qi': params.qi,
        'di': params.di,
        'b': params.b,
        'eur': forecast.eur_oil
    })

# Create comparison table
comparison = pd.DataFrame(results)
print(comparison)
```

## Best Practices

### Data Quality
- Clean production data before analysis (remove outliers, handle gaps)
- Use at least 6-12 months of decline data for reliable fits
- Account for operational events (workovers, chokes, shut-ins)

### Model Selection
- Exponential (b=0): Mature fields, conventional reservoirs
- Hyperbolic (b<1): Most common for unconventional wells
- High b-factors (>1): Unconventional with extended linear flow

### Forecasting
- Validate forecasts against analogous wells
- Consider terminal decline rate for long-term forecasts
- Update forecasts quarterly with new production data

### Uncertainty
- Generate P10/P50/P90 forecasts for reserve booking
- Use Monte Carlo simulation for uncertainty quantification
- Document assumptions and limitations

## Related Skills

- [npv-analyzer](../npv-analyzer/SKILL.md) - Economic evaluation using production forecasts
- [bsee-data-extractor](../bsee-data-extractor/SKILL.md) - Extract historical production data
- [field-analyzer](../field-analyzer/SKILL.md) - Field-level production analysis
- [well-production-dashboard](../well-production-dashboard/SKILL.md) - Production visualization

---

## Version History

- **1.0.0** (2025-12-30): Initial release with Arps decline models, type curves, and forecasting
