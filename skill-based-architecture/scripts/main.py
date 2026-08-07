#!/usr/bin/env python3
"""Data pipeline orchestration tool with configuration validation."""

import argparse
import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validate pipeline configuration structure."""
    
    REQUIRED_KEYS = ['name', 'version', 'steps']
    STEP_REQUIRED_KEYS = ['id', 'type']
    VALID_TYPES = {'transform', 'load', 'extract'}
    
    @classmethod
    def validate(cls, config: Dict[str, Any]) -> bool:
        """Validate configuration dictionary. Returns True if valid, raises ValueError otherwise."""
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")
        
        for key in cls.REQUIRED_KEYS:
            if key not in config:
                raise ValueError(f"Missing required key: {key}")
        
        if not isinstance(config['name'], str) or not config['name'].strip():
            raise ValueError("'name' must be a non-empty string")
        
        if not isinstance(config['version'], str) or not config['version'].strip():
            raise ValueError("'version' must be a non-empty string")
        
        if not isinstance(config['steps'], list) or len(config['steps']) == 0:
            raise ValueError("'steps' must be a non-empty list")
        
        for step in config['steps']:
            cls._validate_step(step)
        
        return True
    
    @classmethod
    def _validate_step(cls, step: Dict[str, Any]) -> None:
        """Validate a single step."""
        if not isinstance(step, dict):
            raise ValueError("Each step must be a dictionary")
        
        for key in cls.STEP_REQUIRED_KEYS:
            if key not in step:
                raise ValueError(f"Step missing required key: {key}")
        
        if not isinstance(step['id'], str) or not step['id'].strip():
            raise ValueError("Step 'id' must be a non-empty string")
        
        if step['type'] not in cls.VALID_TYPES:
            raise ValueError(f"Invalid step type: {step['type']}. Must be one of {cls.VALID_TYPES}")
        
        if 'params' in step and not isinstance(step['params'], dict):
            raise ValueError("Step 'params' must be a dictionary if present")


def load_config(path: Path) -> Dict[str, Any]:
    """Load and parse JSON configuration file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file {path}: {e}")


def run_pipeline(config_path: Optional[Path] = None, config: Optional[Dict[str, Any]] = None) -> int:
    """Run the pipeline with given config file or dict."""
    try:
        if config is None:
            if config_path is None:
                raise ValueError("Either config_path or config must be provided")
            config = load_config(config_path)
        
        ConfigValidator.validate(config)
        logger.info("Configuration validated successfully")
        logger.info(f"Pipeline: {config['name']} v{config['version']}")
        logger.info(f"Total steps: {len(config['steps'])}")
        
        for step in config['steps']:
            logger.info(f"Executing step [{step['id']}] type={step['type']}")
            # In a real implementation, this would execute the actual pipeline logic
        
        logger.info("Pipeline completed successfully")
        return 0
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


def run_selftest() -> int:
    """Run built-in self-tests without external dependencies."""
    logger.info("Running self-tests...")
    
    # Test 1: Valid configuration
    valid_config = {
        "name": "test-pipeline",
        "version": "1.0",
        "steps": [
            {"id": "extract-data", "type": "extract"},
            {"id": "transform-data", "type": "transform", "params": {"method": "normalize"}},
            {"id": "load-data", "type": "load"}
        ]
    }
    try:
        ConfigValidator.validate(valid_config)
        logger.info("Test 1 passed: Valid config accepted")
    except ValueError as e:
        logger.error(f"Test 1 failed: {e}")
        return 1
    
    # Test 2: Missing required key
    invalid_config_missing_key = {
        "name": "test",
        "steps": []
    }
    try:
        ConfigValidator.validate(invalid_config_missing_key)
        logger.error("Test 2 failed: Missing 'version' key not detected")
        return 1
    except ValueError as e:
        if 'version' in str(e):
            logger.info("Test 2 passed: Missing key detected")
        else:
            logger.error(f"Test 2 failed: Unexpected error: {e}")
            return 1
    
    # Test 3: Invalid step type
    invalid_step_type = {
        "name": "test",
        "version": "1.0",
        "steps": [{"id": "bad-step", "type": "invalid-type"}]
    }
    try:
        ConfigValidator.validate(invalid_step_type)
        logger.error("Test 3 failed: Invalid step type not detected")
        return 1
    except ValueError as e:
        if 'Invalid step type' in str(e):
            logger.info("Test 3 passed: Invalid step type detected")
        else:
            logger.error(f"Test 3 failed: Unexpected error: {e}")
            return 1
    
    # Test 4: Empty steps list
    empty_steps = {
        "name": "test",
        "version": "1.0",
        "steps": []
    }
    try:
        ConfigValidator.validate(empty_steps)
        logger.error("Test 4 failed: Empty steps list not detected")
        return 1
    except ValueError as e:
        if 'non-empty list' in str(e):
            logger.info("Test 4 passed: Empty steps detected")
        else:
            logger.error(f"Test 4 failed: Unexpected error: {e}")
            return 1
    
    # Test 5: Invalid params type
    invalid_params = {
        "name": "test",
        "version": "1.0",
        "steps": [{"id": "step1", "type": "transform", "params": "not-a-dict"}]
    }
    try:
        ConfigValidator.validate(invalid_params)
        logger.error("Test 5 failed: Invalid params type not detected")
        return 1
    except ValueError as e:
        if 'params' in str(e):
            logger.info("Test 5 passed: Invalid params detected")
        else:
            logger.error(f"Test 5 failed: Unexpected error: {e}")
            return 1
    
    logger.info("All self-tests passed!")
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Data pipeline orchestration tool")
    parser.add_argument('--config', '-c', type=Path, help='Path to JSON configuration file')
    parser.add_argument('--selftest', action='store_true', help='Run self-tests and exit')
    
    args = parser.parse_args()
    
    if args.selftest:
        return run_selftest()
    
    if not args.config:
        parser.error("Either --config or --selftest must be provided")
        return 2
    
    return run_pipeline(config_path=args.config)


if __name__ == '__main__':
    sys.exit(main())
