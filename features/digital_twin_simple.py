"""
Simplified Digital Twin for Testing
A basic version of the digital twin functionality for testing purposes.
"""

import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

class DigitalTwin:
    """Simplified digital twin for testing"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path)
        self.entities: Dict[str, Any] = {}
        self.relationships: List[Any] = []
        self.last_analysis: Optional[datetime] = None
    
    def _get_source_files(self) -> List[Path]:
        """Get all source files in the workspace"""
        source_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp'}
        ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'build', 'dist'}
        
        source_files = []
        
        try:
            for root, dirs, files in os.walk(self.workspace_path):
                # Remove ignored directories
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in source_extensions:
                        source_files.append(file_path)
        except Exception:
            pass
        
        return source_files

# Global digital twin instance
digital_twin = DigitalTwin()
