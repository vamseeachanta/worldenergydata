"""
Progress tracking and status reporting for verification workflows.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from loguru import logger


class StepStatus(Enum):
    """Status enumeration for workflow steps."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    
    def is_terminal(self) -> bool:
        """Check if status is terminal."""
        return self in [self.COMPLETED, self.FAILED, self.SKIPPED, self.CANCELLED]
    
    def is_successful(self) -> bool:
        """Check if status represents success."""
        return self in [self.COMPLETED, self.SKIPPED]


@dataclass
class StepMetrics:
    """Metrics for individual workflow steps."""
    
    step_name: str
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0
    attempts: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    
    def start(self) -> None:
        """Mark step as started."""
        self.start_time = datetime.now()
        self.status = StepStatus.IN_PROGRESS
        self.attempts += 1
    
    def complete(self) -> None:
        """Mark step as completed."""
        self.end_time = datetime.now()
        self.status = StepStatus.COMPLETED
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
    
    def fail(self, error: str) -> None:
        """Mark step as failed."""
        self.end_time = datetime.now()
        self.status = StepStatus.FAILED
        self.error_count += 1
        self.last_error = error
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
    
    def skip(self) -> None:
        """Mark step as skipped."""
        self.status = StepStatus.SKIPPED
        self.end_time = datetime.now()


class ProgressTracker:
    """
    Track progress of workflow execution.
    """
    
    def __init__(self, total_steps: int):
        """
        Initialize progress tracker.
        
        Args:
            total_steps: Total number of steps in workflow
        """
        self.total_steps = total_steps
        self.completed_steps = 0
        self.failed_steps = 0
        self.skipped_steps = 0
        self.current_step: Optional[str] = None
        
        self.step_metrics: Dict[str, StepMetrics] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Track step order for reporting
        self.step_order: List[str] = []
        
    def start_tracking(self) -> None:
        """Start progress tracking."""
        self.start_time = datetime.now()
        logger.info(f"Started progress tracking for {self.total_steps} steps")
    
    def mark_step_started(self, step_name: str) -> None:
        """
        Mark a step as started.
        
        Args:
            step_name: Name of the step
        """
        if step_name not in self.step_metrics:
            self.step_metrics[step_name] = StepMetrics(step_name)
            self.step_order.append(step_name)
        
        self.step_metrics[step_name].start()
        self.current_step = step_name
        logger.debug(f"Started step: {step_name}")
    
    def mark_completed(self, step_name: str) -> None:
        """
        Mark a step as completed.
        
        Args:
            step_name: Name of the completed step
        """
        if step_name not in self.step_metrics:
            self.step_metrics[step_name] = StepMetrics(step_name)
            self.step_order.append(step_name)
        
        self.step_metrics[step_name].complete()
        self.completed_steps += 1
        
        if self.current_step == step_name:
            self.current_step = None
        
        logger.debug(f"Completed step: {step_name}")
    
    def mark_failed(self, step_name: str, error: Optional[str] = None) -> None:
        """
        Mark a step as failed.
        
        Args:
            step_name: Name of the failed step
            error: Error message
        """
        if step_name not in self.step_metrics:
            self.step_metrics[step_name] = StepMetrics(step_name)
            self.step_order.append(step_name)
        
        self.step_metrics[step_name].fail(error or "Unknown error")
        self.failed_steps += 1
        
        if self.current_step == step_name:
            self.current_step = None
        
        logger.warning(f"Failed step: {step_name} - {error}")
    
    def mark_skipped(self, step_name: str) -> None:
        """
        Mark a step as skipped.
        
        Args:
            step_name: Name of the skipped step
        """
        if step_name not in self.step_metrics:
            self.step_metrics[step_name] = StepMetrics(step_name)
            self.step_order.append(step_name)
        
        self.step_metrics[step_name].skip()
        self.skipped_steps += 1
        
        if self.current_step == step_name:
            self.current_step = None
        
        logger.debug(f"Skipped step: {step_name}")
    
    def get_percentage(self) -> float:
        """
        Get completion percentage.
        
        Returns:
            Percentage of steps completed (including skipped)
        """
        if self.total_steps == 0:
            return 0
        
        progress_steps = self.completed_steps + self.skipped_steps
        return (progress_steps / self.total_steps) * 100
    
    def get_report(self) -> Dict[str, Any]:
        """
        Get detailed progress report.
        
        Returns:
            Progress report dictionary
        """
        report = {
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "percentage": self.get_percentage(),
            "current_step": self.current_step,
            "status": self._get_overall_status(),
            "metrics": {}
        }
        
        # Add step metrics
        for step_name in self.step_order:
            if step_name in self.step_metrics:
                metric = self.step_metrics[step_name]
                report["metrics"][step_name] = {
                    "status": metric.status.value,
                    "duration_seconds": metric.duration_seconds,
                    "attempts": metric.attempts,
                    "error_count": metric.error_count,
                    "last_error": metric.last_error
                }
        
        # Add timing information
        if self.start_time:
            report["start_time"] = self.start_time.isoformat()
            report["elapsed_seconds"] = (datetime.now() - self.start_time).total_seconds()
        
        if self.end_time:
            report["end_time"] = self.end_time.isoformat()
            report["total_duration_seconds"] = (self.end_time - self.start_time).total_seconds()
        
        return report
    
    def estimate_time_remaining(self) -> Optional[float]:
        """
        Estimate time remaining based on average step duration.
        
        Returns:
            Estimated seconds remaining, or None if cannot estimate
        """
        if self.completed_steps == 0 or not self.start_time:
            return None
        
        # Calculate average time per step
        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_time_per_step = elapsed / self.completed_steps
        
        # Calculate remaining steps
        remaining_steps = self.total_steps - self.completed_steps - self.skipped_steps
        
        if remaining_steps <= 0:
            return 0
        
        return avg_time_per_step * remaining_steps
    
    def get_failed_steps(self) -> List[str]:
        """
        Get list of failed step names.
        
        Returns:
            List of failed step names
        """
        return [
            name for name, metric in self.step_metrics.items()
            if metric.status == StepStatus.FAILED
        ]
    
    def get_successful_steps(self) -> List[str]:
        """
        Get list of successful step names.
        
        Returns:
            List of successful step names
        """
        return [
            name for name, metric in self.step_metrics.items()
            if metric.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
        ]
    
    def _get_overall_status(self) -> str:
        """
        Determine overall workflow status.
        
        Returns:
            Overall status string
        """
        if self.failed_steps > 0:
            return "failed"
        elif self.completed_steps + self.skipped_steps >= self.total_steps:
            return "completed"
        elif self.completed_steps > 0 or self.skipped_steps > 0 or self.current_step:
            return "in_progress"
        else:
            return "pending"
    
    def format_summary(self) -> str:
        """
        Format a human-readable progress summary.
        
        Returns:
            Formatted summary string
        """
        percentage = self.get_percentage()
        status = self._get_overall_status()
        
        summary = f"Progress: {percentage:.1f}% ({self.completed_steps}/{self.total_steps} steps)\n"
        summary += f"Status: {status.upper()}\n"
        
        if self.current_step:
            summary += f"Current Step: {self.current_step}\n"
        
        if self.failed_steps > 0:
            summary += f"Failed Steps: {self.failed_steps}\n"
            failed_list = self.get_failed_steps()
            for step in failed_list:
                error = self.step_metrics[step].last_error
                summary += f"  - {step}: {error}\n"
        
        if self.skipped_steps > 0:
            summary += f"Skipped Steps: {self.skipped_steps}\n"
        
        # Add time estimate
        remaining = self.estimate_time_remaining()
        if remaining is not None:
            if remaining > 0:
                summary += f"Estimated Time Remaining: {self._format_duration(remaining)}\n"
            else:
                summary += "Almost complete!\n"
        
        return summary
    
    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in human-readable format.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{seconds:.0f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"