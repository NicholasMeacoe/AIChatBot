"""
AI-Powered Chain of Thought & Task Decomposition Feature
Breaks down complex tasks into manageable steps with user approval and execution tracking.
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import google.generativeai as genai
from datetime import datetime
import asyncio
import threading

class TaskStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepType(Enum):
    ANALYSIS = "analysis"
    CODE_EXECUTION = "code_execution"
    FILE_OPERATION = "file_operation"
    WEB_SEARCH = "web_search"
    API_CALL = "api_call"
    USER_INPUT = "user_input"
    VALIDATION = "validation"

@dataclass
class TaskStep:
    id: str
    title: str
    description: str
    step_type: StepType
    dependencies: List[str]  # IDs of steps that must complete first
    estimated_time: int  # in seconds
    tools_required: List[str]
    parameters: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class Task:
    id: str
    title: str
    description: str
    original_request: str
    steps: List[TaskStep]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    updated_at: datetime = None
    total_estimated_time: int = 0
    progress: float = 0.0

class ChainOfThoughtManager:
    """Manages task decomposition and step-by-step execution"""
    
    def __init__(self, model_name: str = "gemini-2.5-pro-exp-03-25"):
        self.model_name = model_name
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.step_executors: Dict[StepType, Callable] = {
            StepType.ANALYSIS: self._execute_analysis_step,
            StepType.CODE_EXECUTION: self._execute_code_step,
            StepType.FILE_OPERATION: self._execute_file_step,
            StepType.WEB_SEARCH: self._execute_search_step,
            StepType.API_CALL: self._execute_api_step,
            StepType.USER_INPUT: self._execute_user_input_step,
            StepType.VALIDATION: self._execute_validation_step
        }
        
    async def decompose_task(self, user_request: str) -> Task:
        """Decompose a complex user request into manageable steps"""
        
        decomposition_prompt = f"""
        You are an expert task decomposition AI. Break down the following user request into a detailed, step-by-step plan.
        
        User Request: {user_request}
        
        Please provide a JSON response with the following structure:
        {{
            "title": "Brief title for the overall task",
            "description": "Detailed description of what needs to be accomplished",
            "steps": [
                {{
                    "title": "Step title",
                    "description": "Detailed description of this step",
                    "step_type": "analysis|code_execution|file_operation|web_search|api_call|user_input|validation",
                    "dependencies": ["step_id1", "step_id2"],
                    "estimated_time": 30,
                    "tools_required": ["tool1", "tool2"],
                    "parameters": {{"key": "value"}}
                }}
            ]
        }}
        
        Guidelines:
        - Break complex tasks into 3-10 manageable steps
        - Each step should be specific and actionable
        - Include dependencies between steps
        - Estimate realistic time requirements
        - Specify required tools and parameters
        - Consider validation and testing steps
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(decomposition_prompt)
            
            # Parse the JSON response
            task_data = json.loads(response.text.strip())
            
            # Create task steps
            steps = []
            for i, step_data in enumerate(task_data.get('steps', [])):
                step = TaskStep(
                    id=f"step_{i+1}",
                    title=step_data.get('title', f'Step {i+1}'),
                    description=step_data.get('description', ''),
                    step_type=StepType(step_data.get('step_type', 'analysis')),
                    dependencies=step_data.get('dependencies', []),
                    estimated_time=step_data.get('estimated_time', 60),
                    tools_required=step_data.get('tools_required', []),
                    parameters=step_data.get('parameters', {})
                )
                steps.append(step)
            
            # Create the main task
            task = Task(
                id=str(uuid.uuid4()),
                title=task_data.get('title', 'Complex Task'),
                description=task_data.get('description', ''),
                original_request=user_request,
                steps=steps,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                total_estimated_time=sum(step.estimated_time for step in steps)
            )
            
            self.active_tasks[task.id] = task
            return task
            
        except Exception as e:
            # Fallback: create a simple single-step task
            fallback_step = TaskStep(
                id="step_1",
                title="Process Request",
                description=f"Process the user request: {user_request}",
                step_type=StepType.ANALYSIS,
                dependencies=[],
                estimated_time=60,
                tools_required=["ai_model"],
                parameters={"request": user_request}
            )
            
            task = Task(
                id=str(uuid.uuid4()),
                title="User Request",
                description=user_request,
                original_request=user_request,
                steps=[fallback_step],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                total_estimated_time=60
            )
            
            self.active_tasks[task.id] = task
            return task
    
    def approve_task(self, task_id: str, approved_steps: List[str] = None) -> bool:
        """Approve a task for execution (optionally approve specific steps)"""
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        
        if approved_steps is None:
            # Approve all steps
            for step in task.steps:
                step.status = TaskStatus.APPROVED
        else:
            # Approve specific steps
            for step in task.steps:
                if step.id in approved_steps:
                    step.status = TaskStatus.APPROVED
        
        task.status = TaskStatus.APPROVED
        task.updated_at = datetime.now()
        return True
    
    def modify_task(self, task_id: str, modifications: Dict[str, Any]) -> bool:
        """Allow user to modify task steps before execution"""
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        
        # Apply modifications
        if 'title' in modifications:
            task.title = modifications['title']
        
        if 'description' in modifications:
            task.description = modifications['description']
        
        if 'steps' in modifications:
            # Update specific steps
            for step_mod in modifications['steps']:
                step_id = step_mod.get('id')
                for step in task.steps:
                    if step.id == step_id:
                        for key, value in step_mod.items():
                            if hasattr(step, key) and key != 'id':
                                setattr(step, key, value)
        
        task.updated_at = datetime.now()
        return True
    
    async def execute_task(self, task_id: str, progress_callback: Callable = None) -> Dict[str, Any]:
        """Execute an approved task step by step"""
        if task_id not in self.active_tasks:
            return {"error": "Task not found"}
        
        task = self.active_tasks[task_id]
        
        if task.status != TaskStatus.APPROVED:
            return {"error": "Task not approved for execution"}
        
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.now()
        
        execution_log = []
        completed_steps = set()
        
        try:
            # Execute steps in dependency order
            while len(completed_steps) < len(task.steps):
                # Find next executable step
                next_step = None
                for step in task.steps:
                    if (step.status == TaskStatus.APPROVED and 
                        step.id not in completed_steps and
                        all(dep in completed_steps for dep in step.dependencies)):
                        next_step = step
                        break
                
                if next_step is None:
                    # No more executable steps - check for circular dependencies
                    remaining_steps = [s for s in task.steps if s.id not in completed_steps]
                    if remaining_steps:
                        execution_log.append({
                            "error": f"Cannot execute remaining steps due to unmet dependencies: {[s.id for s in remaining_steps]}"
                        })
                    break
                
                # Execute the step
                step_result = await self._execute_step(next_step)
                execution_log.append({
                    "step_id": next_step.id,
                    "step_title": next_step.title,
                    "result": step_result
                })
                
                if step_result.get("success", False):
                    next_step.status = TaskStatus.COMPLETED
                    next_step.completed_at = datetime.now()
                    completed_steps.add(next_step.id)
                else:
                    next_step.status = TaskStatus.FAILED
                    next_step.error = step_result.get("error", "Unknown error")
                    # Decide whether to continue or stop
                    if step_result.get("critical", False):
                        break
                
                # Update progress
                task.progress = len(completed_steps) / len(task.steps)
                if progress_callback:
                    progress_callback(task.progress, next_step.title)
            
            # Update final task status
            if len(completed_steps) == len(task.steps):
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED
            
            task.updated_at = datetime.now()
            
            # Move to completed tasks
            self.completed_tasks[task_id] = task
            del self.active_tasks[task_id]
            
            return {
                "success": task.status == TaskStatus.COMPLETED,
                "task": asdict(task),
                "execution_log": execution_log
            }
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.updated_at = datetime.now()
            return {
                "success": False,
                "error": str(e),
                "execution_log": execution_log
            }
    
    async def _execute_step(self, step: TaskStep) -> Dict[str, Any]:
        """Execute a single step based on its type"""
        step.status = TaskStatus.IN_PROGRESS
        step.started_at = datetime.now()
        
        try:
            executor = self.step_executors.get(step.step_type)
            if executor:
                result = await executor(step)
                step.result = result
                return result
            else:
                return {
                    "success": False,
                    "error": f"No executor found for step type: {step.step_type}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_analysis_step(self, step: TaskStep) -> Dict[str, Any]:
        """Execute an analysis step using AI"""
        try:
            model = genai.GenerativeModel(self.model_name)
            prompt = f"""
            Analysis Task: {step.title}
            Description: {step.description}
            Parameters: {json.dumps(step.parameters)}
            
            Please provide a detailed analysis and any insights or recommendations.
            """
            
            response = model.generate_content(prompt)
            return {
                "success": True,
                "analysis": response.text,
                "type": "analysis"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_code_step(self, step: TaskStep) -> Dict[str, Any]:
        """Execute a code execution step"""
        # This would integrate with the notebook manager
        from .notebook import notebook_manager
        
        code = step.parameters.get('code', '')
        if not code:
            return {
                "success": False,
                "error": "No code provided for execution"
            }
        
        try:
            result = notebook_manager.execute_code(code, step.id)
            return {
                "success": result.get('error') is None,
                "result": result,
                "type": "code_execution"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_file_step(self, step: TaskStep) -> Dict[str, Any]:
        """Execute a file operation step"""
        operation = step.parameters.get('operation', 'read')
        file_path = step.parameters.get('file_path', '')
        
        try:
            if operation == 'read':
                with open(file_path, 'r') as f:
                    content = f.read()
                return {
                    "success": True,
                    "content": content,
                    "type": "file_read"
                }
            elif operation == 'write':
                content = step.parameters.get('content', '')
                with open(file_path, 'w') as f:
                    f.write(content)
                return {
                    "success": True,
                    "message": f"File written: {file_path}",
                    "type": "file_write"
                }
            else:
                return {
                    "success": False,
                    "error": f"Unsupported file operation: {operation}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_search_step(self, step: TaskStep) -> Dict[str, Any]:
        """Execute a web search step"""
        # This would integrate with existing search functionality
        query = step.parameters.get('query', '')
        
        try:
            # Placeholder for search implementation
            return {
                "success": True,
                "query": query,
                "results": [],
                "type": "web_search"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_api_step(self, step: TaskStep) -> Dict[str, Any]:
        """Execute an API call step"""
        import requests
        
        url = step.parameters.get('url', '')
        method = step.parameters.get('method', 'GET')
        headers = step.parameters.get('headers', {})
        data = step.parameters.get('data', {})
        
        try:
            response = requests.request(method, url, headers=headers, json=data)
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                "type": "api_call"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_user_input_step(self, step: TaskStep) -> Dict[str, Any]:
        """Execute a user input step (requires user interaction)"""
        return {
            "success": True,
            "message": "User input required",
            "prompt": step.parameters.get('prompt', 'Please provide input'),
            "type": "user_input",
            "requires_interaction": True
        }
    
    async def _execute_validation_step(self, step: TaskStep) -> Dict[str, Any]:
        """Execute a validation step"""
        validation_type = step.parameters.get('type', 'generic')
        target = step.parameters.get('target', '')
        
        try:
            # Implement different validation types
            if validation_type == 'code_syntax':
                import ast
                ast.parse(target)
                return {
                    "success": True,
                    "message": "Code syntax is valid",
                    "type": "validation"
                }
            elif validation_type == 'file_exists':
                import os
                exists = os.path.exists(target)
                return {
                    "success": exists,
                    "message": f"File {'exists' if exists else 'does not exist'}: {target}",
                    "type": "validation"
                }
            else:
                return {
                    "success": True,
                    "message": f"Generic validation passed for: {target}",
                    "type": "validation"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a task"""
        task = self.active_tasks.get(task_id) or self.completed_tasks.get(task_id)
        if task:
            return asdict(task)
        return None
    
    def list_active_tasks(self) -> List[Dict[str, Any]]:
        """List all active tasks"""
        return [asdict(task) for task in self.active_tasks.values()]
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel an active task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = TaskStatus.CANCELLED
            task.updated_at = datetime.now()
            self.completed_tasks[task_id] = task
            del self.active_tasks[task_id]
            return True
        return False

# Global chain of thought manager instance
chain_of_thought_manager = ChainOfThoughtManager()
