"""
Import Deduplicator - Removes duplicate imports from fixed test files
"""

import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def deduplicate_imports(file_path: Path) -> bool:
    """Remove duplicate imports from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix duplicate function imports in from statements
        # Pattern: "function1, function1, function1, function2, function2"
        import_match = re.search(
            r'from worldenergydata\..*? import (.+?)(?:\n|$)', 
            content, 
            re.MULTILINE
        )
        
        if import_match:
            imports_str = import_match.group(1)
            # Split by comma and deduplicate
            imports = [i.strip() for i in imports_str.split(',')]
            # Remove duplicates while preserving order
            seen = set()
            unique_imports = []
            for imp in imports:
                if imp not in seen:
                    seen.add(imp)
                    unique_imports.append(imp)
            
            # Only update if there were duplicates
            if len(unique_imports) < len(imports):
                new_imports_str = ', '.join(unique_imports)
                old_line = f'import {imports_str}'
                new_line = f'import {new_imports_str}'
                content = content.replace(old_line, new_line)
        
        # Fix duplicate "import pytest" lines
        lines = content.split('\n')
        new_lines = []
        seen_imports = set()
        
        for line in lines:
            # Check if it's an import line
            if line.strip() == 'import pytest':
                if 'import pytest' not in seen_imports:
                    new_lines.append(line)
                    seen_imports.add('import pytest')
                # else skip duplicate
            else:
                new_lines.append(line)
        
        content = '\n'.join(new_lines)
        
        # Fix the setup_method signature issue
        # It should be either setup_method(self, method) or setup_method(self)
        # Not setup_method(self, method, tmp_path)
        content = re.sub(
            r'def setup_method\(self, method, tmp_path\):',
            'def setup_method(self, method):',
            content
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"  ✓ Deduplicated imports in {file_path.name}")
            return True
        return False
        
    except Exception as e:
        logger.error(f"  ✗ Error processing {file_path.name}: {str(e)}")
        return False


def main():
    """Main function to deduplicate imports in all AI-generated tests."""
    
    dirs_to_process = [
        Path('tests/ai_generated/unit'),
        Path('tests/ai_generated/integration')
    ]
    
    total_fixed = 0
    total_files = 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"IMPORT DEDUPLICATOR")
    logger.info(f"{'='*60}\n")
    
    for test_dir in dirs_to_process:
        if test_dir.exists():
            test_files = list(test_dir.glob('test_*.py'))
            total_files += len(test_files)
            
            for test_file in test_files:
                if deduplicate_imports(test_file):
                    total_fixed += 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total files processed: {total_files}")
    logger.info(f"Files fixed: {total_fixed}")
    

if __name__ == "__main__":
    main()