"""
Paleowells Data Visualizer

Provides visualization capabilities for paleontological well data analysis.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class PaleowellsVisualizer:
    """Visualize paleontological well data from the Gulf of Mexico."""
    
    def __init__(self, style: str = 'seaborn-v0_8'):
        """
        Initialize the visualizer with a specific style.
        
        Args:
            style: Matplotlib style to use
        """
        plt.style.use(style)
        sns.set_palette("husl")
        
    def plot_wells_by_epoch(self, df: pd.DataFrame, 
                           save_path: Optional[Path] = None,
                           figsize: Tuple[int, int] = (12, 8)) -> plt.Figure:
        """
        Create a bar plot of wells by geological epoch.
        
        Args:
            df: DataFrame with paleo well data
            save_path: Optional path to save the figure
            figsize: Figure size as (width, height)
            
        Returns:
            Matplotlib figure object
        """
        # Extract epoch from Paleo Age
        df['Epoch'] = df['Paleo Age'].str.extract(r'(Paleocene|Eocene|Oligocene|Miocene|Pliocene)')
        
        # Count unique wells by epoch
        epoch_counts = df.groupby('Epoch')['API Well Number'].nunique().sort_values(ascending=False)
        
        fig, ax = plt.subplots(figsize=figsize)
        epoch_counts.plot(kind='bar', ax=ax, color='steelblue')
        
        ax.set_title('Distribution of Wells by Geological Epoch', fontsize=16, fontweight='bold')
        ax.set_xlabel('Geological Epoch', fontsize=12)
        ax.set_ylabel('Number of Unique Wells', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for i, v in enumerate(epoch_counts.values):
            ax.text(i, v + 0.5, str(v), ha='center', va='bottom')
            
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Figure saved to {save_path}")
            
        return fig
        
    def plot_depth_distribution(self, df: pd.DataFrame,
                               depth_type: str = 'True Vertical Depth',
                               save_path: Optional[Path] = None,
                               figsize: Tuple[int, int] = (14, 8)) -> plt.Figure:
        """
        Create depth distribution plots by epoch.
        
        Args:
            df: DataFrame with paleo well data
            depth_type: 'True Vertical Depth' or 'Measured Depth'
            save_path: Optional path to save the figure
            figsize: Figure size
            
        Returns:
            Matplotlib figure object
        """
        # Extract epoch
        df['Epoch'] = df['Paleo Age'].str.extract(r'(Paleocene|Eocene|Oligocene|Miocene|Pliocene)')
        
        # Clean depth data (convert to numeric)
        df[depth_type] = pd.to_numeric(df[depth_type], errors='coerce')
        
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        
        # Box plot
        df.boxplot(column=depth_type, by='Epoch', ax=axes[0])
        axes[0].set_title(f'{depth_type} Distribution by Epoch')
        axes[0].set_xlabel('Geological Epoch')
        axes[0].set_ylabel(f'{depth_type} (ft)')
        axes[0].grid(True, alpha=0.3)
        
        # Histogram with epoch overlay
        for epoch in df['Epoch'].dropna().unique():
            epoch_data = df[df['Epoch'] == epoch][depth_type].dropna()
            axes[1].hist(epoch_data, alpha=0.5, label=epoch, bins=30)
            
        axes[1].set_title(f'{depth_type} Distribution Overlay')
        axes[1].set_xlabel(f'{depth_type} (ft)')
        axes[1].set_ylabel('Frequency')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.suptitle('Depth Analysis of Paleowells', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Figure saved to {save_path}")
            
        return fig
        
    def plot_classification_pie(self, df: pd.DataFrame,
                               save_path: Optional[Path] = None,
                               figsize: Tuple[int, int] = (10, 8)) -> plt.Figure:
        """
        Create a pie chart of Definite vs Possible classifications.
        
        Args:
            df: DataFrame with paleo well data
            save_path: Optional path to save the figure
            figsize: Figure size
            
        Returns:
            Matplotlib figure object
        """
        classification_counts = df['Definite/Possible'].value_counts()
        
        fig, ax = plt.subplots(figsize=figsize)
        
        colors = ['#2ecc71', '#e74c3c', '#3498db']
        wedges, texts, autotexts = ax.pie(
            classification_counts.values,
            labels=classification_counts.index,
            autopct='%1.1f%%',
            colors=colors[:len(classification_counts)],
            startangle=90
        )
        
        # Enhance text
        for text in texts:
            text.set_fontsize(12)
        for autotext in autotexts:
            autotext.set_fontsize(11)
            autotext.set_fontweight('bold')
            autotext.set_color('white')
            
        ax.set_title('Classification Distribution: Definite vs Possible', 
                    fontsize=14, fontweight='bold')
        
        # Add a legend with counts
        legend_labels = [f'{label}: {count:,} ({count/classification_counts.sum()*100:.1f}%)'
                        for label, count in classification_counts.items()]
        ax.legend(legend_labels, loc='best', fontsize=10)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Figure saved to {save_path}")
            
        return fig
        
    def create_comprehensive_report(self, df: pd.DataFrame,
                                  output_directory: Path) -> Dict[str, Path]:
        """
        Generate a comprehensive visual report of the paleowells data.
        
        Args:
            df: DataFrame with paleo well data
            output_directory: Directory to save all figures
            
        Returns:
            Dictionary mapping figure names to their paths
        """
        output_directory = Path(output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        
        figures = {}
        
        # Generate all visualizations
        try:
            # Wells by epoch
            epoch_fig = self.plot_wells_by_epoch(
                df, 
                save_path=output_directory / "wells_by_epoch.png"
            )
            figures['wells_by_epoch'] = output_directory / "wells_by_epoch.png"
            plt.close(epoch_fig)
            
            # Depth distributions
            tvd_fig = self.plot_depth_distribution(
                df,
                depth_type='True Vertical Depth',
                save_path=output_directory / "true_vertical_depth_distribution.png"
            )
            figures['tvd_distribution'] = output_directory / "true_vertical_depth_distribution.png"
            plt.close(tvd_fig)
            
            md_fig = self.plot_depth_distribution(
                df,
                depth_type='Measured Depth',
                save_path=output_directory / "measured_depth_distribution.png"
            )
            figures['md_distribution'] = output_directory / "measured_depth_distribution.png"
            plt.close(md_fig)
            
            # Classification pie chart
            class_fig = self.plot_classification_pie(
                df,
                save_path=output_directory / "classification_distribution.png"
            )
            figures['classification'] = output_directory / "classification_distribution.png"
            plt.close(class_fig)
            
            logger.info(f"Comprehensive report generated with {len(figures)} figures")
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            raise
            
        return figures