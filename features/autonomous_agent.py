"""
Proactive & Autonomous Agent Mode
Allows the AI to autonomously work towards high-level goals with minimal supervision.
"""

import os
import json
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import google.generativeai as genai
from datetime import datetime, timedelta
import threading
import queue
import subprocess
import ast
import re
from pathlib import Path

class AgentMode(Enum):
    REACTIVE = "reactive"  # Standard chat mode
    PROACTIVE = "proactive"  # Agent suggests next actions
    AUTONOMOUS = "autonomous"  # Agent works independently

class ActionType(Enum):
    ANALYZE_CODEBASE = "analyze_codebase"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE_CODE = "execute_code"
    RUN_TESTS = "run_tests"
    SEARCH_DOCUMENTATION = "search_documentation"
    REFACTOR_CODE = "refactor_code"
    CREATE_BRANCH = "create_branch"
    COMMIT_CHANGES = "commit_changes"
    INSTALL_DEPENDENCY = "install_dependency"
    VALIDATE_CHANGES = "validate_changes"

@dataclass
class AgentAction:
    id: str
    action_type: ActionType
    description: str
    parameters: Dict[str, Any]
    reasoning: str
    confidence: float  # 0.0 to 1.0
    estimated_time: int  # seconds
    dependencies: List[str]  # IDs of actions that must complete first
    status: str = "pending"  # pending, executing, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = None

@dataclass
class AgentGoal:
    id: str
    title: str
    description: str
    success_criteria: List[str]
    constraints: List[str]
    priority: int  # 1-10, higher is more important
    deadline: Optional[datetime] = None
    status: str = "active"  # active, completed, failed, paused
    progress: float = 0.0
    actions: List[AgentAction] = None
    created_at: datetime = None

class AutonomousAgent:
    """Manages autonomous operation and goal-directed behavior"""
    
    def __init__(self, model_name: str = "gemini-2.5-pro-exp-03-25", workspace_path: str = "."):
        self.model_name = model_name
        self.workspace_path = Path(workspace_path)
        self.mode = AgentMode.REACTIVE
        self.active_goals: Dict[str, AgentGoal] = {}
        self.completed_goals: Dict[str, AgentGoal] = {}
        self.action_queue = queue.PriorityQueue()
        self.is_running = False
        self.commentary_callback: Optional[Callable] = None
        self.approval_callback: Optional[Callable] = None
        self.require_approval = True
        self.max_autonomous_actions = 10  # Safety limit
        self.action_count = 0
        
        # Initialize codebase knowledge
        self.codebase_knowledge = {}
        self.file_dependencies = {}
        self.project_structure = {}
        
    def set_mode(self, mode: AgentMode):
        """Set the agent's operating mode"""
        self.mode = mode
        if mode == AgentMode.AUTONOMOUS and not self.is_running:
            self.start_autonomous_loop()
        elif mode != AgentMode.AUTONOMOUS and self.is_running:
            self.stop_autonomous_loop()
    
    def add_goal(self, title: str, description: str, success_criteria: List[str], 
                 constraints: List[str] = None, priority: int = 5, 
                 deadline: Optional[datetime] = None) -> str:
        """Add a new goal for the agent to work towards"""
        goal_id = f"goal_{len(self.active_goals) + len(self.completed_goals) + 1}"
        
        goal = AgentGoal(
            id=goal_id,
            title=title,
            description=description,
            success_criteria=success_criteria,
            constraints=constraints or [],
            priority=priority,
            deadline=deadline,
            actions=[],
            created_at=datetime.now()
        )
        
        self.active_goals[goal_id] = goal
        
        # Generate initial action plan
        asyncio.create_task(self._generate_action_plan(goal))
        
        return goal_id
    
    async def _generate_action_plan(self, goal: AgentGoal):
        """Generate a detailed action plan for achieving a goal"""
        
        # First, analyze the current codebase
        await self._analyze_codebase()
        
        planning_prompt = f"""
        You are an autonomous software development agent. Generate a detailed action plan to achieve the following goal:
        
        Goal: {goal.title}
        Description: {goal.description}
        Success Criteria: {json.dumps(goal.success_criteria)}
        Constraints: {json.dumps(goal.constraints)}
        
        Current Codebase Analysis:
        {json.dumps(self.codebase_knowledge, indent=2)}
        
        Project Structure:
        {json.dumps(self.project_structure, indent=2)}
        
        Generate a JSON response with the following structure:
        {{
            "actions": [
                {{
                    "action_type": "analyze_codebase|read_file|write_file|execute_code|run_tests|search_documentation|refactor_code|create_branch|commit_changes|install_dependency|validate_changes",
                    "description": "Detailed description of what this action accomplishes",
                    "parameters": {{"key": "value"}},
                    "reasoning": "Why this action is necessary",
                    "confidence": 0.8,
                    "estimated_time": 120,
                    "dependencies": ["action_1", "action_2"]
                }}
            ]
        }}
        
        Guidelines:
        - Break the goal into 5-15 specific, actionable steps
        - Consider the current state of the codebase
        - Include validation and testing steps
        - Respect the given constraints
        - Provide clear reasoning for each action
        - Estimate realistic time requirements
        - Consider dependencies between actions
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(planning_prompt)
            
            plan_data = json.loads(response.text.strip())
            
            actions = []
            for i, action_data in enumerate(plan_data.get('actions', [])):
                action = AgentAction(
                    id=f"{goal.id}_action_{i+1}",
                    action_type=ActionType(action_data.get('action_type', 'analyze_codebase')),
                    description=action_data.get('description', ''),
                    parameters=action_data.get('parameters', {}),
                    reasoning=action_data.get('reasoning', ''),
                    confidence=action_data.get('confidence', 0.5),
                    estimated_time=action_data.get('estimated_time', 60),
                    dependencies=action_data.get('dependencies', []),
                    timestamp=datetime.now()
                )
                actions.append(action)
            
            goal.actions = actions
            
            # Add actions to the queue
            for action in actions:
                priority = goal.priority * action.confidence
                self.action_queue.put((priority, action))
            
            if self.commentary_callback:
                self.commentary_callback(f"Generated action plan for goal '{goal.title}' with {len(actions)} actions")
                
        except Exception as e:
            if self.commentary_callback:
                self.commentary_callback(f"Failed to generate action plan: {str(e)}")
    
    async def _analyze_codebase(self):
        """Analyze the current codebase to understand its structure and content"""
        try:
            # Get project structure
            self.project_structure = self._get_project_structure()
            
            # Analyze key files
            key_files = self._identify_key_files()
            
            analysis_results = {}
            for file_path in key_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Basic analysis
                    analysis = {
                        'lines': len(content.split('\n')),
                        'size': len(content),
                        'language': self._detect_language(file_path),
                        'functions': self._extract_functions(content, file_path),
                        'classes': self._extract_classes(content, file_path),
                        'imports': self._extract_imports(content, file_path),
                        'last_modified': os.path.getmtime(file_path)
                    }
                    
                    analysis_results[str(file_path)] = analysis
                    
                except Exception as e:
                    analysis_results[str(file_path)] = {'error': str(e)}
            
            self.codebase_knowledge = analysis_results
            
            if self.commentary_callback:
                self.commentary_callback(f"Analyzed {len(analysis_results)} files in the codebase")
                
        except Exception as e:
            if self.commentary_callback:
                self.commentary_callback(f"Codebase analysis failed: {str(e)}")
    
    def _get_project_structure(self) -> Dict[str, Any]:
        """Get the project directory structure"""
        structure = {}
        
        try:
            for root, dirs, files in os.walk(self.workspace_path):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
                
                rel_root = os.path.relpath(root, self.workspace_path)
                if rel_root == '.':
                    rel_root = ''
                
                structure[rel_root] = {
                    'directories': dirs,
                    'files': files
                }
        except Exception as e:
            structure['error'] = str(e)
        
        return structure
    
    def _identify_key_files(self) -> List[Path]:
        """Identify key files in the project for analysis"""
        key_files = []
        
        # Common important files
        important_patterns = [
            '*.py', '*.js', '*.ts', '*.java', '*.cpp', '*.c', '*.h',
            'requirements.txt', 'package.json', 'Dockerfile', 'README.md',
            'setup.py', 'main.py', 'app.py', 'index.js', 'index.html'
        ]
        
        for pattern in important_patterns:
            key_files.extend(self.workspace_path.glob(f"**/{pattern}"))
        
        # Limit to reasonable number of files
        return key_files[:50]
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect the programming language of a file"""
        extension = file_path.suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.md': 'markdown'
        }
        return language_map.get(extension, 'unknown')
    
    def _extract_functions(self, content: str, file_path: Path) -> List[str]:
        """Extract function names from code"""
        functions = []
        
        if file_path.suffix == '.py':
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        functions.append(node.name)
            except:
                # Fallback to regex
                functions = re.findall(r'def\s+(\w+)\s*\(', content)
        elif file_path.suffix in ['.js', '.ts']:
            functions = re.findall(r'function\s+(\w+)\s*\(', content)
            functions.extend(re.findall(r'(\w+)\s*:\s*function\s*\(', content))
            functions.extend(re.findall(r'const\s+(\w+)\s*=\s*\(.*?\)\s*=>', content))
        
        return functions
    
    def _extract_classes(self, content: str, file_path: Path) -> List[str]:
        """Extract class names from code"""
        classes = []
        
        if file_path.suffix == '.py':
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        classes.append(node.name)
            except:
                classes = re.findall(r'class\s+(\w+)', content)
        elif file_path.suffix in ['.js', '.ts']:
            classes = re.findall(r'class\s+(\w+)', content)
        elif file_path.suffix == '.java':
            classes = re.findall(r'class\s+(\w+)', content)
        
        return classes
    
    def _extract_imports(self, content: str, file_path: Path) -> List[str]:
        """Extract import statements from code"""
        imports = []
        
        if file_path.suffix == '.py':
            imports = re.findall(r'(?:from\s+(\S+)\s+)?import\s+([^\n]+)', content)
            imports = [f"{imp[0]}.{imp[1]}" if imp[0] else imp[1] for imp in imports]
        elif file_path.suffix in ['.js', '.ts']:
            imports = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', content)
            imports.extend(re.findall(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', content))
        
        return imports
    
    def start_autonomous_loop(self):
        """Start the autonomous execution loop"""
        if self.is_running:
            return
        
        self.is_running = True
        self.action_count = 0
        
        def autonomous_worker():
            while self.is_running and self.action_count < self.max_autonomous_actions:
                try:
                    # Get next action from queue (with timeout)
                    try:
                        priority, action = self.action_queue.get(timeout=5.0)
                    except queue.Empty:
                        continue
                    
                    # Check if action dependencies are met
                    if not self._dependencies_met(action):
                        # Put back in queue with lower priority
                        self.action_queue.put((priority * 0.9, action))
                        continue
                    
                    # Request approval if required
                    if self.require_approval and self.approval_callback:
                        approved = self.approval_callback(action)
                        if not approved:
                            continue
                    
                    # Execute the action
                    asyncio.run(self._execute_action(action))
                    self.action_count += 1
                    
                    # Brief pause between actions
                    time.sleep(1)
                    
                except Exception as e:
                    if self.commentary_callback:
                        self.commentary_callback(f"Error in autonomous loop: {str(e)}")
        
        # Start the worker thread
        self.worker_thread = threading.Thread(target=autonomous_worker, daemon=True)
        self.worker_thread.start()
        
        if self.commentary_callback:
            self.commentary_callback("Autonomous agent mode activated")
    
    def stop_autonomous_loop(self):
        """Stop the autonomous execution loop"""
        self.is_running = False
        if self.commentary_callback:
            self.commentary_callback("Autonomous agent mode deactivated")
    
    def _dependencies_met(self, action: AgentAction) -> bool:
        """Check if all dependencies for an action are met"""
        for dep_id in action.dependencies:
            # Find the dependency action
            dep_action = None
            for goal in self.active_goals.values():
                for a in goal.actions:
                    if a.id == dep_id:
                        dep_action = a
                        break
                if dep_action:
                    break
            
            if not dep_action or dep_action.status != "completed":
                return False
        
        return True
    
    async def _execute_action(self, action: AgentAction):
        """Execute a single action"""
        action.status = "executing"
        
        if self.commentary_callback:
            self.commentary_callback(f"Executing: {action.description}")
        
        try:
            if action.action_type == ActionType.ANALYZE_CODEBASE:
                await self._analyze_codebase()
                result = {"analysis": "Codebase analysis completed"}
            
            elif action.action_type == ActionType.READ_FILE:
                file_path = action.parameters.get('file_path', '')
                with open(file_path, 'r') as f:
                    content = f.read()
                result = {"content": content, "file_path": file_path}
            
            elif action.action_type == ActionType.WRITE_FILE:
                file_path = action.parameters.get('file_path', '')
                content = action.parameters.get('content', '')
                with open(file_path, 'w') as f:
                    f.write(content)
                result = {"message": f"File written: {file_path}"}
            
            elif action.action_type == ActionType.EXECUTE_CODE:
                code = action.parameters.get('code', '')
                # Use the notebook manager for code execution
                from .notebook import notebook_manager
                exec_result = notebook_manager.execute_code(code, action.id)
                result = exec_result
            
            elif action.action_type == ActionType.RUN_TESTS:
                test_command = action.parameters.get('command', 'python -m pytest')
                process = subprocess.run(test_command.split(), capture_output=True, text=True)
                result = {
                    "return_code": process.returncode,
                    "stdout": process.stdout,
                    "stderr": process.stderr
                }
            
            else:
                result = {"message": f"Action type {action.action_type} not yet implemented"}
            
            action.result = result
            action.status = "completed"
            
            if self.commentary_callback:
                self.commentary_callback(f"Completed: {action.description}")
                
        except Exception as e:
            action.error = str(e)
            action.status = "failed"
            
            if self.commentary_callback:
                self.commentary_callback(f"Failed: {action.description} - {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the autonomous agent"""
        return {
            "mode": self.mode.value,
            "is_running": self.is_running,
            "active_goals": len(self.active_goals),
            "completed_goals": len(self.completed_goals),
            "actions_executed": self.action_count,
            "queue_size": self.action_queue.qsize()
        }
    
    def get_goals(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all goals (active and completed)"""
        return {
            "active": [asdict(goal) for goal in self.active_goals.values()],
            "completed": [asdict(goal) for goal in self.completed_goals.values()]
        }
    
    def pause_goal(self, goal_id: str) -> bool:
        """Pause a specific goal"""
        if goal_id in self.active_goals:
            self.active_goals[goal_id].status = "paused"
            return True
        return False
    
    def resume_goal(self, goal_id: str) -> bool:
        """Resume a paused goal"""
        if goal_id in self.active_goals:
            goal = self.active_goals[goal_id]
            if goal.status == "paused":
                goal.status = "active"
                # Re-add pending actions to queue
                for action in goal.actions:
                    if action.status == "pending":
                        priority = goal.priority * action.confidence
                        self.action_queue.put((priority, action))
                return True
        return False

# Global autonomous agent instance
autonomous_agent = AutonomousAgent()
