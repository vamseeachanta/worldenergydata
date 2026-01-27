# ABOUTME: Test script demonstrating metocean-visualizer skill wave rose functionality.
# ABOUTME: Generates synthetic wave data and creates interactive Plotly wave rose chart.
"""
Metocean Visualizer Skill Demo - Wave Rose

This test script demonstrates the wave rose visualization pattern from the
metocean-visualizer skill. It generates synthetic wave data and creates
an interactive wave rose using Plotly's go.Barpolar.

Usage:
    uv run python tests/modules/metocean/test_skill_visualizer.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def generate_synthetic_wave_data(
    n_records: int = 5000,
    seed: int = 42
) -> pd.DataFrame:
    """Generate synthetic wave height and direction data.

    Creates realistic-looking wave data with:
    - Dominant swell from SW (225 deg) with secondary from W (270 deg)
    - Wave heights following Rayleigh-like distribution
    - Correlation between direction and wave height

    Args:
        n_records: Number of data points to generate.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with wave_height_m and wave_direction_deg columns.
    """
    np.random.seed(seed)

    # Create bimodal directional distribution
    # Primary swell from SW (225 deg), secondary from W (270 deg)
    n_primary = int(n_records * 0.6)
    n_secondary = int(n_records * 0.25)
    n_random = n_records - n_primary - n_secondary

    # Primary SW swell (centered at 225 deg, std=25)
    dir_primary = np.random.normal(225, 25, n_primary) % 360
    hs_primary = np.random.weibull(2.0, n_primary) * 2.5 + 0.5

    # Secondary W swell (centered at 270 deg, std=20)
    dir_secondary = np.random.normal(270, 20, n_secondary) % 360
    hs_secondary = np.random.weibull(1.8, n_secondary) * 1.8 + 0.3

    # Random background waves from all directions
    dir_random = np.random.uniform(0, 360, n_random)
    hs_random = np.random.weibull(1.5, n_random) * 1.0 + 0.2

    # Combine all data
    directions = np.concatenate([dir_primary, dir_secondary, dir_random])
    heights = np.concatenate([hs_primary, hs_secondary, hs_random])

    # Cap extreme values for realism
    heights = np.clip(heights, 0.1, 12.0)

    # Shuffle to mix data
    indices = np.random.permutation(n_records)

    df = pd.DataFrame({
        'wave_height_m': heights[indices],
        'wave_direction_deg': directions[indices]
    })

    return df


def create_wave_rose(
    df: pd.DataFrame,
    height_col: str = 'wave_height_m',
    direction_col: str = 'wave_direction_deg',
    n_sectors: int = 16,
    output_path: str | None = None
) -> go.Figure:
    """Create interactive wave rose with Plotly.

    Uses go.Barpolar to create a polar bar chart showing wave occurrence
    by direction, with bar color indicating mean wave height.

    Args:
        df: DataFrame containing wave data.
        height_col: Column name for wave height.
        direction_col: Column name for wave direction (degrees, 0=N, clockwise).
        n_sectors: Number of directional sectors (8, 12, 16, or 36 typical).
        output_path: Path to save HTML output. If None, not saved.

    Returns:
        Plotly Figure object.
    """
    sector_width = 360 / n_sectors
    bins = np.arange(0, 360 + sector_width, sector_width)

    # Bin directions into sectors
    df_copy = df.copy()
    df_copy['dir_bin'] = pd.cut(
        df_copy[direction_col],
        bins=bins,
        labels=bins[:-1] + sector_width / 2
    )

    # Calculate statistics per sector
    stats = df_copy.groupby('dir_bin', observed=True).agg({
        height_col: ['count', 'mean', 'max']
    }).reset_index()
    stats.columns = ['direction', 'count', 'mean_hs', 'max_hs']

    # Convert direction to float
    stats['direction'] = stats['direction'].astype(float)

    # Calculate occurrence percentage
    total = stats['count'].sum()
    stats['occurrence_pct'] = 100 * stats['count'] / total

    # Create the wave rose figure
    fig = go.Figure()

    fig.add_trace(go.Barpolar(
        r=stats['occurrence_pct'],
        theta=stats['direction'],
        width=sector_width * 0.9,
        marker_color=stats['mean_hs'],
        marker_colorscale='Viridis',
        marker_colorbar=dict(
            title=dict(text='Mean Hs (m)', side='right'),
            ticksuffix=' m',
            thickness=20
        ),
        hovertemplate=(
            '<b>Direction:</b> %{theta:.0f} deg<br>'
            '<b>Occurrence:</b> %{r:.1f}%<br>'
            '<b>Mean Hs:</b> %{marker.color:.2f} m'
            '<extra></extra>'
        ),
        name='Wave Rose'
    ))

    # Configure polar layout for meteorological convention
    # (0=North at top, clockwise)
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, stats['occurrence_pct'].max() * 1.15],
                ticksuffix='%',
                showline=False,
                gridcolor='lightgray'
            ),
            angularaxis=dict(
                direction='clockwise',
                rotation=90,  # Put 0 deg (North) at top
                tickmode='array',
                tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                ticktext=['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
                gridcolor='lightgray'
            ),
            bgcolor='rgba(255,255,255,0.9)'
        ),
        title=dict(
            text='Wave Rose - Direction Distribution',
            x=0.5,
            font=dict(size=18)
        ),
        showlegend=False,
        margin=dict(l=80, r=80, t=80, b=60),
        paper_bgcolor='white'
    )

    # Add summary annotation
    summary_text = (
        f"Records: {total:,}<br>"
        f"Mean Hs: {df[height_col].mean():.2f} m<br>"
        f"Max Hs: {df[height_col].max():.2f} m"
    )
    fig.add_annotation(
        text=summary_text,
        xref='paper', yref='paper',
        x=0.02, y=0.98,
        showarrow=False,
        font=dict(size=11),
        align='left',
        bgcolor='rgba(255,255,255,0.8)',
        bordercolor='gray',
        borderwidth=1,
        borderpad=5
    )

    if output_path:
        fig.write_html(output_path)
        print(f"Wave rose saved to: {output_path}")

    return fig


def main() -> None:
    """Generate wave rose demo and save to HTML."""
    # Define output path
    output_dir = Path('/mnt/github/workspace-hub/worldenergydata/reports/metocean')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'test_wave_rose.html'

    print("Generating synthetic wave data...")
    df = generate_synthetic_wave_data(n_records=5000)

    print(f"Data summary:")
    print(f"  Records: {len(df)}")
    print(f"  Wave height range: {df['wave_height_m'].min():.2f} - {df['wave_height_m'].max():.2f} m")
    print(f"  Mean wave height: {df['wave_height_m'].mean():.2f} m")
    print(f"  Direction range: {df['wave_direction_deg'].min():.1f} - {df['wave_direction_deg'].max():.1f} deg")

    print("\nCreating wave rose visualization...")
    fig = create_wave_rose(
        df,
        n_sectors=16,
        output_path=str(output_path)
    )

    print(f"\nDone! Open the HTML file to view the interactive wave rose.")


if __name__ == '__main__':
    main()
