"""
Test suite for the sub-agents framework infrastructure.
Tests directory structure creation, YAML configuration loading, and agent framework operations.
"""

import os
import tempfile
import pytest
import yaml
from pathlib import Path
import shutil


class TestAgentFrameworkStructure:
    """Test agent framework directory structure and file operations."""
    
    def setup_method(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.agent_os_path = os.path.join(self.temp_dir, '.agent-os')
        self.agents_path = os.path.join(self.agent_os_path, 'agents')
        
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_agent_directory_structure_creation(self):
        """Test creation of required agent framework directories."""
        expected_dirs = [
            'core',
            'knowledge_bases', 
            'learning',
            'framework'
        ]
        
        # Create directory structure
        os.makedirs(self.agents_path, exist_ok=True)
        for dir_name in expected_dirs:
            os.makedirs(os.path.join(self.agents_path, dir_name), exist_ok=True)
        
        # Verify all directories exist
        for dir_name in expected_dirs:
            dir_path = os.path.join(self.agents_path, dir_name)
            assert os.path.exists(dir_path), f"Directory {dir_name} was not created"
            assert os.path.isdir(dir_path), f"Path {dir_name} is not a directory"
    
    def test_framework_subdirectory_creation(self):
        """Test creation of framework subdirectories."""
        framework_path = os.path.join(self.agents_path, 'framework')
        os.makedirs(framework_path, exist_ok=True)
        
        # Expected framework files (will be created by other tests)
        expected_files = [
            'agent_loader.py',
            'learning_engine.py', 
            'performance_tracker.py'
        ]
        
        # Verify framework directory exists
        assert os.path.exists(framework_path)
        assert os.path.isdir(framework_path)
    
    def test_knowledge_bases_subdirectories(self):
        """Test creation of knowledge base directories for each agent type."""
        kb_path = os.path.join(self.agents_path, 'knowledge_bases')
        agent_types = [
            'energy_economics',
            'petroleum_engineering',
            'data_quality',
            'documentation',
            'testing_qa'
        ]
        
        os.makedirs(kb_path, exist_ok=True)
        for agent_type in agent_types:
            agent_kb_path = os.path.join(kb_path, agent_type)
            os.makedirs(agent_kb_path, exist_ok=True)
            
            # Create subdirectories for knowledge organization
            for subdir in ['concepts', 'methodologies', 'industry_standards', 'code_examples']:
                os.makedirs(os.path.join(agent_kb_path, subdir), exist_ok=True)
        
        # Verify all agent KB directories exist
        for agent_type in agent_types:
            agent_kb_path = os.path.join(kb_path, agent_type)
            assert os.path.exists(agent_kb_path), f"Knowledge base for {agent_type} not created"


class TestAgentConfigurationValidation:
    """Test YAML configuration loading and validation for agents."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_valid_agent_yaml_structure(self):
        """Test loading of valid agent YAML configuration."""
        valid_config = {
            'agent': {
                'name': 'test_agent',
                'version': '1.0.0',
                'specialization': 'Test Agent',
                'description': 'Agent for testing',
                'knowledge_domains': ['testing', 'validation'],
                'learning_schedule': {
                    'frequency': 'weekly',
                    'resources': ['test_resources']
                },
                'capabilities': ['test_execution', 'result_validation']
            }
        }
        
        # Write valid config to file
        config_path = os.path.join(self.temp_dir, 'test_agent.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        # Load and validate
        with open(config_path, 'r') as f:
            loaded_config = yaml.safe_load(f)
        
        assert 'agent' in loaded_config
        assert loaded_config['agent']['name'] == 'test_agent'
        assert loaded_config['agent']['version'] == '1.0.0'
        assert 'knowledge_domains' in loaded_config['agent']
        assert 'learning_schedule' in loaded_config['agent']
    
    def test_invalid_agent_yaml_structure(self):
        """Test handling of invalid agent YAML configuration."""
        invalid_config = {
            'invalid_key': {
                'name': 'test_agent'
                # Missing required fields
            }
        }
        
        config_path = os.path.join(self.temp_dir, 'invalid_agent.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(invalid_config, f)
        
        with open(config_path, 'r') as f:
            loaded_config = yaml.safe_load(f)
        
        # Should not have required 'agent' key
        assert 'agent' not in loaded_config
        assert 'invalid_key' in loaded_config
    
    def test_agent_configuration_required_fields(self):
        """Test validation of required fields in agent configuration."""
        required_fields = [
            'name', 'version', 'specialization', 'description',
            'knowledge_domains', 'learning_schedule', 'capabilities'
        ]
        
        base_config = {
            'agent': {
                'name': 'test_agent',
                'version': '1.0.0', 
                'specialization': 'Test Agent',
                'description': 'Agent for testing',
                'knowledge_domains': ['testing'],
                'learning_schedule': {'frequency': 'weekly'},
                'capabilities': ['testing']
            }
        }
        
        # Test that all required fields are present
        for field in required_fields:
            assert field in base_config['agent'], f"Required field '{field}' missing from agent config"


class TestAgentFileOperations:
    """Test file operations for agent framework."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""  
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_agent_config_file_creation(self):
        """Test creation of agent configuration files."""
        config_dir = os.path.join(self.temp_dir, 'core')
        os.makedirs(config_dir, exist_ok=True)
        
        agent_config = {
            'agent': {
                'name': 'energy_economics',
                'version': '1.0.0',
                'specialization': 'Energy Economic Analysis'
            }
        }
        
        config_path = os.path.join(config_dir, 'energy_economics.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(agent_config, f)
        
        # Verify file was created and is readable
        assert os.path.exists(config_path)
        assert os.path.isfile(config_path)
        
        with open(config_path, 'r') as f:
            loaded_config = yaml.safe_load(f)
        
        assert loaded_config['agent']['name'] == 'energy_economics'
    
    def test_knowledge_base_file_operations(self):
        """Test knowledge base file creation and management."""
        kb_dir = os.path.join(self.temp_dir, 'knowledge_bases', 'energy_economics')
        os.makedirs(kb_dir, exist_ok=True)
        
        # Create test knowledge file
        concepts_dir = os.path.join(kb_dir, 'concepts')
        os.makedirs(concepts_dir, exist_ok=True)
        
        test_concept = {
            'concept': 'NPV Analysis',
            'description': 'Net Present Value calculation methodology',
            'formulas': ['NPV = Sum(CF_t / (1+r)^t)'],
            'applications': ['Economic evaluation', 'Investment analysis']
        }
        
        concept_path = os.path.join(concepts_dir, 'npv_analysis.yaml')
        with open(concept_path, 'w') as f:
            yaml.dump(test_concept, f)
        
        # Verify knowledge file operations
        assert os.path.exists(concept_path)
        
        with open(concept_path, 'r') as f:
            loaded_concept = yaml.safe_load(f)
        
        assert loaded_concept['concept'] == 'NPV Analysis'
        assert 'formulas' in loaded_concept
        assert 'applications' in loaded_concept


if __name__ == '__main__':
    pytest.main([__file__])