"""
Digital Twin of the Codebase Feature - Part 1
Creates and maintains a comprehensive mental model of the entire codebase.
"""

import os
import ast
import json
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import networkx as nx
from collections import defaultdict, Counter
import google.generativeai as genai
import re

@dataclass
class CodeEntity:
    id: str
    name: str
    entity_type: str  # class, function, variable, module, file
    file_path: str
    line_start: int
    line_end: int
    signature: str = ""
    docstring: str = ""
    complexity: int = 0
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_modified: datetime = field(default_factory=datetime.now)

@dataclass
class CodeRelationship:
    source_id: str
    target_id: str
    relationship_type: str  # calls, inherits, imports, uses, contains
    strength: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ArchitecturalPattern:
    pattern_name: str
    description: str
    entities_involved: List[str]
    confidence: float
    evidence: List[str]

@dataclass
class CodebaseSnapshot:
    timestamp: datetime
    total_files: int
    total_lines: int
    total_entities: int
    total_relationships: int
    complexity_metrics: Dict[str, float]
    architectural_patterns: List[ArchitecturalPattern]
    health_score: float

class DigitalTwin:
    """Maintains a comprehensive digital twin of the codebase"""
    
    def __init__(self, workspace_path: str = ".", model_name: str = "gemini-2.5-pro-exp-03-25"):
        self.workspace_path = Path(workspace_path)
        self.model_name = model_name
        
        # Core data structures
        self.entities: Dict[str, CodeEntity] = {}
        self.relationships: List[CodeRelationship] = []
        self.knowledge_graph = nx.DiGraph()
        
        # Analysis results
        self.architectural_patterns: List[ArchitecturalPattern] = []
        self.complexity_metrics: Dict[str, float] = {}
        self.health_metrics: Dict[str, float] = {}
        
        # Tracking
        self.file_hashes: Dict[str, str] = {}
        self.last_analysis: Optional[datetime] = None
        self.snapshots: List[CodebaseSnapshot] = []
        
        # Language parsers
        self.parsers = {
            '.py': self._parse_python_file,
            '.js': self._parse_javascript_file,
            '.ts': self._parse_typescript_file,
            '.java': self._parse_java_file,
            '.cpp': self._parse_cpp_file,
            '.c': self._parse_c_file
        }
    
    def _get_source_files(self) -> List[Path]:
        """Get all source files in the workspace"""
        
        source_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp'}
        ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'build', 'dist'}
        
        source_files = []
        
        for root, dirs, files in os.walk(self.workspace_path):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in source_extensions:
                    source_files.append(file_path)
        
        return source_files

# Global digital twin instance
digital_twin = DigitalTwin()
        
        # Scan and analyze files
        analysis_results = await self._analyze_codebase()
        
        # Build knowledge graph
        self._build_knowledge_graph()
        
        # Detect architectural patterns
        await self._detect_architectural_patterns()
        
        # Calculate metrics
        self._calculate_complexity_metrics()
        self._calculate_health_metrics()
        
        # Create snapshot
        snapshot = self._create_snapshot()
        self.snapshots.append(snapshot)
        
        # Update tracking
        self.last_analysis = datetime.now()
        
        build_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "status": "completed",
            "build_time": build_time,
            "entities_found": len(self.entities),
            "relationships_found": len(self.relationships),
            "files_analyzed": analysis_results["files_analyzed"],
            "patterns_detected": len(self.architectural_patterns),
            "health_score": self.health_metrics.get("overall_health", 0.0)
        }
    
    def _needs_rebuild(self) -> bool:
        """Check if the codebase has changed and needs rebuilding"""
        
        if not self.last_analysis:
            return True
        
        # Check for new or modified files
        for file_path in self._get_source_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                current_hash = hashlib.md5(content.encode()).hexdigest()
                stored_hash = self.file_hashes.get(str(file_path))
                
                if current_hash != stored_hash:
                    return True
                    
            except Exception:
                continue
        
        return False
    
    def _clear_twin_data(self):
        """Clear all twin data for rebuild"""
        self.entities.clear()
        self.relationships.clear()
        self.knowledge_graph.clear()
        self.architectural_patterns.clear()
        self.complexity_metrics.clear()
        self.health_metrics.clear()
    
    async def _analyze_codebase(self) -> Dict[str, Any]:
        """Analyze all source files in the codebase"""
        
        files_analyzed = 0
        entities_found = 0
        
        for file_path in self._get_source_files():
            try:
                # Update file hash
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.file_hashes[str(file_path)] = hashlib.md5(content.encode()).hexdigest()
                
                # Parse file based on extension
                file_extension = file_path.suffix.lower()
                if file_extension in self.parsers:
                    file_entities = await self.parsers[file_extension](file_path, content)
                    entities_found += len(file_entities)
                    files_analyzed += 1
                
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
                continue
        
        return {
            "files_analyzed": files_analyzed,
            "entities_found": entities_found
        }
    
    def _get_source_files(self) -> List[Path]:
        """Get all source files in the workspace"""
        
        source_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp'}
        ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'build', 'dist'}
        
        source_files = []
        
        for root, dirs, files in os.walk(self.workspace_path):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in source_extensions:
                    source_files.append(file_path)
        
        return source_files
    
    async def _parse_python_file(self, file_path: Path, content: str) -> List[CodeEntity]:
        """Parse a Python file and extract entities"""
        
        entities = []
        
        try:
            tree = ast.parse(content)
            
            # Extract classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    entity = CodeEntity(
                        id=f"{file_path}:class:{node.name}",
                        name=node.name,
                        entity_type="class",
                        file_path=str(file_path),
                        line_start=node.lineno,
                        line_end=getattr(node, 'end_lineno', node.lineno),
                        docstring=ast.get_docstring(node) or "",
                        complexity=self._calculate_node_complexity(node)
                    )
                    
                    # Extract base classes
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            entity.dependencies.add(base.id)
                    
                    entities.append(entity)
                    self.entities[entity.id] = entity
                
                elif isinstance(node, ast.FunctionDef):
                    # Skip nested functions for now
                    if not any(isinstance(parent, (ast.ClassDef, ast.FunctionDef)) 
                             for parent in ast.walk(tree) if hasattr(parent, 'body') and node in getattr(parent, 'body', [])):
                        
                        entity = CodeEntity(
                            id=f"{file_path}:function:{node.name}",
                            name=node.name,
                            entity_type="function",
                            file_path=str(file_path),
                            line_start=node.lineno,
                            line_end=getattr(node, 'end_lineno', node.lineno),
                            signature=self._get_function_signature(node),
                            docstring=ast.get_docstring(node) or "",
                            complexity=self._calculate_node_complexity(node)
                        )
                        
                        entities.append(entity)
                        self.entities[entity.id] = entity
            
            # Extract imports and create relationships
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    self._process_import_node(node, file_path)
            
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        
        return entities
    
    async def _parse_javascript_file(self, file_path: Path, content: str) -> List[CodeEntity]:
        """Parse a JavaScript file (basic implementation)"""
        
        entities = []
        
        # Basic regex-based parsing for JavaScript
        # This is a simplified implementation - a full parser would be better
        
        # Find function declarations
        function_pattern = r'function\s+(\w+)\s*\([^)]*\)\s*{'
        for match in re.finditer(function_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            
            entity = CodeEntity(
                id=f"{file_path}:function:{match.group(1)}",
                name=match.group(1),
                entity_type="function",
                file_path=str(file_path),
                line_start=line_num,
                line_end=line_num,  # Simplified
                signature=match.group(0)
            )
            
            entities.append(entity)
            self.entities[entity.id] = entity
        
        # Find class declarations
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{'
        for match in re.finditer(class_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            
            entity = CodeEntity(
                id=f"{file_path}:class:{match.group(1)}",
                name=match.group(1),
                entity_type="class",
                file_path=str(file_path),
                line_start=line_num,
                line_end=line_num,  # Simplified
            )
            
            # Add inheritance relationship
            if match.group(2):
                entity.dependencies.add(match.group(2))
            
            entities.append(entity)
            self.entities[entity.id] = entity
        
        return entities
    
    async def _parse_typescript_file(self, file_path: Path, content: str) -> List[CodeEntity]:
        """Parse a TypeScript file (delegates to JavaScript parser for now)"""
        return await self._parse_javascript_file(file_path, content)
    
    async def _parse_java_file(self, file_path: Path, content: str) -> List[CodeEntity]:
        """Parse a Java file (basic implementation)"""
        
        entities = []
        
        # Find class declarations
        class_pattern = r'(?:public\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?\s*{'
        for match in re.finditer(class_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            
            entity = CodeEntity(
                id=f"{file_path}:class:{match.group(1)}",
                name=match.group(1),
                entity_type="class",
                file_path=str(file_path),
                line_start=line_num,
                line_end=line_num,  # Simplified
            )
            
            # Add inheritance
            if match.group(2):
                entity.dependencies.add(match.group(2))
            
            entities.append(entity)
            self.entities[entity.id] = entity
        
        # Find method declarations
        method_pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*{'
        for match in re.finditer(method_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            
            entity = CodeEntity(
                id=f"{file_path}:method:{match.group(1)}",
                name=match.group(1),
                entity_type="function",
                file_path=str(file_path),
                line_start=line_num,
                line_end=line_num,  # Simplified
                signature=match.group(0)
            )
            
            entities.append(entity)
            self.entities[entity.id] = entity
        
        return entities
    
    async def _parse_cpp_file(self, file_path: Path, content: str) -> List[CodeEntity]:
        """Parse a C++ file (basic implementation)"""
        
        entities = []
        
        # Find class declarations
        class_pattern = r'class\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+(\w+))?\s*{'
        for match in re.finditer(class_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            
            entity = CodeEntity(
                id=f"{file_path}:class:{match.group(1)}",
                name=match.group(1),
                entity_type="class",
                file_path=str(file_path),
                line_start=line_num,
                line_end=line_num,  # Simplified
            )
            
            # Add inheritance
            if match.group(2):
                entity.dependencies.add(match.group(2))
            
            entities.append(entity)
            self.entities[entity.id] = entity
        
        # Find function declarations
        function_pattern = r'(?:[\w:]+\s+)?(\w+)\s*\([^)]*\)\s*{'
        for match in re.finditer(function_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            
            entity = CodeEntity(
                id=f"{file_path}:function:{match.group(1)}",
                name=match.group(1),
                entity_type="function",
                file_path=str(file_path),
                line_start=line_num,
                line_end=line_num,  # Simplified
                signature=match.group(0)
            )
            
            entities.append(entity)
            self.entities[entity.id] = entity
        
        return entities
    
    async def _parse_c_file(self, file_path: Path, content: str) -> List[CodeEntity]:
        """Parse a C file (delegates to C++ parser for basic functionality)"""
        return await self._parse_cpp_file(file_path, content)
    
    def _calculate_node_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of an AST node"""
        
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature from AST node"""
        
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        return f"{node.name}({', '.join(args)})"
    
    def _process_import_node(self, node: ast.AST, file_path: Path):
        """Process import nodes to create relationships"""
        
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Create import relationship
                relationship = CodeRelationship(
                    source_id=str(file_path),
                    target_id=alias.name,
                    relationship_type="imports"
                )
                self.relationships.append(relationship)
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                relationship = CodeRelationship(
                    source_id=str(file_path),
                    target_id=node.module,
                    relationship_type="imports"
                )
                self.relationships.append(relationship)
