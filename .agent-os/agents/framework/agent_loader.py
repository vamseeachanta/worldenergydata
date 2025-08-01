"""
Agent Framework Loader
Handles loading and validation of YAML-based agent configurations.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger


class AgentConfigurationError(Exception):
    """Custom exception for agent configuration errors."""
    pass


class AgentLoader:
    """
    Loads and validates agent configurations from YAML files.
    Provides methods for discovering, loading, and validating agent definitions.
    """
    
    def __init__(self, agents_directory: Optional[str] = None):
        """
        Initialize the AgentLoader.
        
        Args:
            agents_directory: Path to the agents directory. If None, uses default location.
        """
        if agents_directory is None:
            # Default to .agent-os/agents relative to project root
            self.agents_dir = Path(__file__).parent.parent
        else:
            self.agents_dir = Path(agents_directory)
        
        self.core_dir = self.agents_dir / 'core'
        self.knowledge_bases_dir = self.agents_dir / 'knowledge_bases'
        
        logger.info(f"AgentLoader initialized with directory: {self.agents_dir}")
    
    def get_available_agents(self) -> List[str]:
        """
        Get list of available agent names from core directory.
        
        Returns:
            List of agent names (without .yaml extension)
        """
        if not self.core_dir.exists():
            logger.warning(f"Core directory does not exist: {self.core_dir}")
            return []
        
        agent_files = list(self.core_dir.glob('*.yaml'))
        agent_names = [f.stem for f in agent_files]
        
        logger.info(f"Found {len(agent_names)} available agents: {agent_names}")
        return agent_names
    
    def load_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Load agent configuration from YAML file.
        
        Args:
            agent_name: Name of the agent to load
            
        Returns:
            Dictionary containing agent configuration
            
        Raises:
            AgentConfigurationError: If agent file not found or invalid
        """
        config_path = self.core_dir / f"{agent_name}.yaml"
        
        if not config_path.exists():
            raise AgentConfigurationError(f"Agent configuration not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise AgentConfigurationError(f"Empty configuration file: {config_path}")
            
            # Validate configuration structure
            self._validate_agent_config(config, agent_name)
            
            logger.info(f"Successfully loaded agent configuration: {agent_name}")
            return config
            
        except yaml.YAMLError as e:
            raise AgentConfigurationError(f"Invalid YAML in {config_path}: {e}")
        except Exception as e:
            raise AgentConfigurationError(f"Error loading agent {agent_name}: {e}")
    
    def _validate_agent_config(self, config: Dict[str, Any], agent_name: str) -> None:
        """
        Validate agent configuration structure and required fields.
        
        Args:
            config: Agent configuration dictionary
            agent_name: Name of the agent for error reporting
            
        Raises:
            AgentConfigurationError: If configuration is invalid
        """
        if 'agent' not in config:
            raise AgentConfigurationError(f"Missing 'agent' key in {agent_name} configuration")
        
        agent_config = config['agent']
        required_fields = [
            'name', 'version', 'specialization', 'description',
            'knowledge_domains', 'learning_schedule', 'capabilities'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in agent_config:
                missing_fields.append(field)
        
        if missing_fields:
            raise AgentConfigurationError(
                f"Missing required fields in {agent_name}: {missing_fields}"
            )
        
        # Validate specific field types
        if not isinstance(agent_config['knowledge_domains'], list):
            raise AgentConfigurationError(
                f"'knowledge_domains' must be a list in {agent_name}"
            )
        
        if not isinstance(agent_config['capabilities'], list):
            raise AgentConfigurationError(
                f"'capabilities' must be a list in {agent_name}"
            )
        
        learning_schedule = agent_config['learning_schedule']
        if not isinstance(learning_schedule, dict):
            raise AgentConfigurationError(
                f"'learning_schedule' must be a dictionary in {agent_name}"
            )
        
        if 'frequency' not in learning_schedule:
            raise AgentConfigurationError(
                f"'frequency' required in learning_schedule for {agent_name}"
            )
        
        logger.debug(f"Agent configuration validation passed for: {agent_name}")
    
    def load_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all available agent configurations.
        
        Returns:
            Dictionary mapping agent names to their configurations
        """
        agents = {}
        agent_names = self.get_available_agents()
        
        for agent_name in agent_names:
            try:
                agents[agent_name] = self.load_agent_config(agent_name)
            except AgentConfigurationError as e:
                logger.error(f"Failed to load agent {agent_name}: {e}")
                continue
        
        logger.info(f"Successfully loaded {len(agents)} agents out of {len(agent_names)} available")
        return agents
    
    def get_agent_knowledge_base_path(self, agent_name: str) -> Path:
        """
        Get the knowledge base directory path for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Path to the agent's knowledge base directory
        """
        kb_path = self.knowledge_bases_dir / agent_name
        
        if not kb_path.exists():
            logger.warning(f"Knowledge base directory does not exist: {kb_path}")
        
        return kb_path
    
    def validate_agent_setup(self, agent_name: str) -> bool:
        """
        Validate that an agent is properly set up with all required components.
        
        Args:
            agent_name: Name of the agent to validate
            
        Returns:
            True if agent is properly configured, False otherwise
        """
        try:
            # Check if configuration exists and is valid
            config = self.load_agent_config(agent_name)
            
            # Check if knowledge base directory exists
            kb_path = self.get_agent_knowledge_base_path(agent_name)
            if not kb_path.exists():
                logger.warning(f"Knowledge base missing for agent: {agent_name}")
                return False
            
            # Check for required knowledge base subdirectories
            required_subdirs = ['concepts', 'methodologies', 'industry_standards', 'code_examples']
            for subdir in required_subdirs:
                subdir_path = kb_path / subdir
                if not subdir_path.exists():
                    logger.warning(f"Missing knowledge base subdirectory: {subdir_path}")
                    return False
            
            logger.info(f"Agent validation passed for: {agent_name}")
            return True
            
        except AgentConfigurationError as e:
            logger.error(f"Agent validation failed for {agent_name}: {e}")
            return False
    
    def create_agent_template(self, agent_name: str, specialization: str, 
                            description: str, knowledge_domains: List[str],
                            capabilities: List[str]) -> Dict[str, Any]:
        """
        Create a template agent configuration.
        
        Args:
            agent_name: Name of the new agent
            specialization: Agent specialization area
            description: Description of the agent's purpose
            knowledge_domains: List of knowledge domains
            capabilities: List of agent capabilities
            
        Returns:
            Dictionary containing the agent template configuration
        """
        template = {
            'agent': {
                'name': agent_name,
                'version': '1.0.0',
                'specialization': specialization,
                'description': description,
                'knowledge_domains': knowledge_domains,
                'learning_schedule': {
                    'frequency': 'weekly',
                    'resources': [
                        'industry_publications',
                        'technical_papers',
                        'code_repositories'
                    ]
                },
                'capabilities': capabilities,
                'created_date': str(Path(__file__).stat().st_mtime),
                'last_updated': str(Path(__file__).stat().st_mtime)
            }
        }
        
        logger.info(f"Created agent template for: {agent_name}")
        return template
    
    def save_agent_config(self, agent_name: str, config: Dict[str, Any]) -> None:
        """
        Save agent configuration to YAML file.
        
        Args:
            agent_name: Name of the agent
            config: Agent configuration dictionary
            
        Raises:
            AgentConfigurationError: If save operation fails
        """
        config_path = self.core_dir / f"{agent_name}.yaml"
        
        try:
            # Ensure core directory exists
            self.core_dir.mkdir(parents=True, exist_ok=True)
            
            # Validate configuration before saving
            self._validate_agent_config(config, agent_name)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Saved agent configuration: {config_path}")
            
        except Exception as e:
            raise AgentConfigurationError(f"Failed to save agent {agent_name}: {e}")


# Convenience function for loading agents
def load_agent(agent_name: str, agents_directory: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to load a single agent configuration.
    
    Args:
        agent_name: Name of the agent to load
        agents_directory: Optional custom agents directory path
        
    Returns:
        Agent configuration dictionary
    """
    loader = AgentLoader(agents_directory)
    return loader.load_agent_config(agent_name)


# Convenience function for loading all agents
def load_all_agents(agents_directory: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Convenience function to load all available agent configurations.
    
    Args:
        agents_directory: Optional custom agents directory path
        
    Returns:
        Dictionary mapping agent names to configurations
    """
    loader = AgentLoader(agents_directory)
    return loader.load_all_agents()