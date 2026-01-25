"""
Collection workflow for SODIR data.

This module provides configurable workflows for collecting SODIR data,
including scheduling, filtering, validation, and storage.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import concurrent.futures
from pathlib import Path

logger = logging.getLogger(__name__)


class CollectionWorkflow:
    """
    Configurable workflow for SODIR data collection.
    
    Supports scheduled collection, filtering, validation, and storage.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize collection workflow with configuration.
        
        Args:
            config: Workflow configuration dictionary
        """
        self.config = config
        self.name = config.get('name', 'default_workflow')
        self.datasets = config.get('datasets', [])
        self.schedule = config.get('schedule', 'daily')
        self.filters = config.get('filters', {})
        self.validation_enabled = config.get('validation', {}).get('enabled', True)
        self.validation_strict = config.get('validation', {}).get('strict', False)
        self.storage_config = config.get('storage', {})
        
        # Initialize components
        self.api_client = None
        self.sodir_data = None
        self.last_execution = None
        self.execution_history = []
        
        logger.info(f"Initialized workflow: {self.name}")
        
    def execute(self) -> Dict[str, Any]:
        """
        Execute the collection workflow.
        
        Returns:
            Execution result with status and collected data
        """
        start_time = datetime.utcnow()
        result = {
            'workflow': self.name,
            'start_time': start_time.isoformat(),
            'success': False,
            'datasets_collected': []
        }
        
        try:
            logger.info(f"Executing workflow: {self.name}")
            
            # Initialize SODIR data component if needed
            if not self.sodir_data:
                from ..data import SodirData
                self.sodir_data = SodirData(self.config)
                
            # Determine datasets to collect
            datasets_to_collect = self._get_datasets_to_collect()
            
            # Collect data for each dataset
            collected_data = {}
            for dataset in datasets_to_collect:
                try:
                    logger.info(f"Collecting dataset: {dataset}")
                    dataset_result = self._collect_dataset_with_workflow(dataset)
                    
                    if dataset_result:
                        collected_data[dataset] = dataset_result
                        result['datasets_collected'].append(dataset)
                        
                except Exception as e:
                    logger.error(f"Failed to collect {dataset}: {str(e)}")
                    result[f'{dataset}_error'] = str(e)
                    
            # Validate collected data if enabled
            if self.validation_enabled and collected_data:
                validation_results = self._validate_collected_data(collected_data)
                result['validation'] = validation_results
                
            # Store data if configured
            if self.storage_config and collected_data:
                storage_results = self._store_collected_data(collected_data)
                result['storage'] = storage_results
                
            # Update execution tracking
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            result['success'] = len(result['datasets_collected']) > 0
            result['end_time'] = end_time.isoformat()
            result['execution_time'] = execution_time
            result['total_records'] = sum(
                len(data.get('data', [])) for data in collected_data.values()
            )
            
            # Track execution history
            self.last_execution = end_time
            self.execution_history.append({
                'timestamp': end_time,
                'success': result['success'],
                'datasets': result['datasets_collected'],
                'duration': execution_time
            })
            
            logger.info(f"Workflow completed: {self.name}, collected {len(result['datasets_collected'])} datasets")
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            result['error'] = str(e)
            result['success'] = False
            
        return result
        
    def collect_parallel(
        self,
        datasets: List[str],
        max_workers: int = 5
    ) -> Dict[str, Dict[str, Any]]:
        """
        Collect multiple datasets in parallel.
        
        Args:
            datasets: List of datasets to collect
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary with results for each dataset
        """
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all collection tasks
            future_to_dataset = {
                executor.submit(self._collect_dataset_with_workflow, dataset): dataset
                for dataset in datasets
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_dataset):
                dataset = future_to_dataset[future]
                try:
                    result = future.result()
                    results[dataset] = result
                    logger.info(f"Successfully collected {dataset}")
                except Exception as e:
                    logger.error(f"Failed to collect {dataset}: {str(e)}")
                    results[dataset] = {'error': str(e), 'status': 'failed'}
                    
        return results
        
    def collect_data(self) -> Dict[str, Any]:
        """
        Collect data according to workflow configuration.
        
        Returns:
            Collection results
        """
        if not self.sodir_data:
            from ..data import SodirData
            self.sodir_data = SodirData(self.config)
            
        # Apply filters based on schedule
        filters = self._prepare_filters()
        
        # Collect datasets
        if len(self.datasets) > 1 and self.config.get('parallel', False):
            return self.collect_parallel(self.datasets)
        else:
            results = {}
            for dataset in self.datasets:
                results[dataset] = self.sodir_data.collect_dataset(
                    dataset,
                    validate=self.validation_enabled,
                    filters=filters
                )
            return results
            
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate collected data.
        
        Args:
            data: Collected data to validate
            
        Returns:
            Validation results
        """
        if not self.sodir_data:
            from ..data import SodirData
            self.sodir_data = SodirData(self.config)
            
        validation_results = {}
        
        for dataset_type, dataset_data in data.items():
            if isinstance(dataset_data, dict) and 'data' in dataset_data:
                report = self.sodir_data.generate_validation_report(
                    dataset_data['data'],
                    dataset_type
                )
                validation_results[dataset_type] = report
                
        return {'valid': all(r.get('validation_rate', 0) > 0.9 for r in validation_results.values()),
                'reports': validation_results}
        
    def store_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store collected data according to workflow configuration.
        
        Args:
            data: Data to store
            
        Returns:
            Storage results
        """
        if not self.sodir_data or not self.sodir_data.storage:
            from ..storage import DataStorage
            self.storage = DataStorage(self.storage_config)
        else:
            self.storage = self.sodir_data.storage
            
        storage_results = {}
        
        for dataset_type, dataset_data in data.items():
            try:
                path = self.storage.save(dataset_type, dataset_data)
                storage_results[dataset_type] = {
                    'success': True,
                    'path': str(path)
                }
            except Exception as e:
                storage_results[dataset_type] = {
                    'success': False,
                    'error': str(e)
                }
                
        return storage_results
        
    def collect_dataset(self, dataset_type: str) -> Dict[str, Any]:
        """
        Collect a single dataset with workflow configuration.
        
        Args:
            dataset_type: Type of dataset to collect
            
        Returns:
            Collection result
        """
        if not self.sodir_data:
            from ..data import SodirData
            self.sodir_data = SodirData(self.config)
            
        filters = self._prepare_filters()
        
        return self.sodir_data.collect_dataset(
            dataset_type,
            validate=self.validation_enabled,
            filters=filters
        )
        
    def _get_datasets_to_collect(self) -> List[str]:
        """
        Determine which datasets to collect based on configuration.
        
        Returns:
            List of dataset types to collect
        """
        # Use configured datasets or default to all
        if self.datasets:
            return self.datasets
            
        # Default datasets
        return ['blocks', 'wellbores', 'fields', 'discoveries', 'surveys']
        
    def _collect_dataset_with_workflow(self, dataset_type: str) -> Dict[str, Any]:
        """
        Collect a dataset with workflow-specific configuration.
        
        Args:
            dataset_type: Type of dataset to collect
            
        Returns:
            Collection result
        """
        # Prepare filters
        filters = self._prepare_filters()
        
        # Determine if we should do incremental collection
        since = None
        if self.schedule in ['daily', 'hourly'] and self.last_execution:
            since = self.last_execution.isoformat()
            
        # Collect data
        result = self.sodir_data.collect_dataset(
            dataset_type,
            validate=self.validation_enabled,
            since=since,
            filters=filters
        )
        
        return result
        
    def _prepare_filters(self) -> Dict[str, Any]:
        """
        Prepare API filters based on workflow configuration.
        
        Returns:
            Dictionary of filters to apply
        """
        filters = self.filters.copy()
        
        # Add time-based filters for incremental collection
        if self.filters.get('updated_since') == 'yesterday':
            yesterday = datetime.utcnow() - timedelta(days=1)
            filters['updated_since'] = yesterday.isoformat()
        elif self.filters.get('updated_since') == 'last_week':
            last_week = datetime.utcnow() - timedelta(days=7)
            filters['updated_since'] = last_week.isoformat()
            
        return filters
        
    def _validate_collected_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all collected data.
        
        Args:
            collected_data: Dictionary of collected data by dataset type
            
        Returns:
            Validation results
        """
        validation_results = {}
        
        for dataset_type, data in collected_data.items():
            if 'validation' in data.get('metadata', {}):
                # Already validated during collection
                validation_results[dataset_type] = data['metadata']['validation']
            elif 'data' in data:
                # Validate now
                report = self.sodir_data.generate_validation_report(
                    data['data'],
                    dataset_type
                )
                validation_results[dataset_type] = report
                
        return validation_results
        
    def _store_collected_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store all collected data.
        
        Args:
            collected_data: Dictionary of collected data by dataset type
            
        Returns:
            Storage results
        """
        if not self.sodir_data.storage:
            from ..storage import DataStorage
            self.sodir_data.storage = DataStorage(self.storage_config)
            
        storage_results = {}
        
        for dataset_type, data in collected_data.items():
            try:
                if 'data' in data and data['data']:
                    path = self.sodir_data.storage.save(dataset_type, data)
                    storage_results[dataset_type] = {
                        'success': True,
                        'path': str(path),
                        'records': len(data['data'])
                    }
                else:
                    storage_results[dataset_type] = {
                        'success': False,
                        'reason': 'No data to store'
                    }
            except Exception as e:
                storage_results[dataset_type] = {
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"Failed to store {dataset_type}: {str(e)}")
                
        return storage_results
        
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get workflow execution history.
        
        Returns:
            List of execution records
        """
        return self.execution_history
        
    def get_next_execution_time(self) -> Optional[datetime]:
        """
        Calculate next scheduled execution time.
        
        Returns:
            Next execution datetime or None
        """
        if not self.last_execution:
            return datetime.utcnow()
            
        if self.schedule == 'hourly':
            return self.last_execution + timedelta(hours=1)
        elif self.schedule == 'daily':
            return self.last_execution + timedelta(days=1)
        elif self.schedule == 'weekly':
            return self.last_execution + timedelta(weeks=1)
            
        return None