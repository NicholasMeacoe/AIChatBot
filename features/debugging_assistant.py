"""
AI-Powered Debugging Assistant Feature
Provides intelligent debugging support with error analysis, stack trace interpretation, and fix suggestions.
"""

import re
import ast
import json
import traceback
import subprocess
import sys
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import google.generativeai as genai
from collections import defaultdict
import difflib

@dataclass
class ErrorInfo:
    error_type: str
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    function_name: Optional[str] = None
    stack_trace: List[str] = field(default_factory=list)
    context_lines: List[str] = field(default_factory=list)
    severity: str = "medium"  # low, medium, high, critical

@dataclass
class DebugSuggestion:
    suggestion_id: str
    title: str
    description: str
    fix_type: str  # code_change, configuration, dependency, environment
    confidence: float  # 0.0 to 1.0
    code_changes: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""
    references: List[str] = field(default_factory=list)
    estimated_time: str = "5-10 minutes"

@dataclass
class DebugSession:
    session_id: str
    started_at: datetime
    error_info: ErrorInfo
    suggestions: List[DebugSuggestion] = field(default_factory=list)
    applied_fixes: List[str] = field(default_factory=list)
    status: str = "active"  # active, resolved, abandoned
    resolution_notes: str = ""

class DebuggingAssistant:
    """AI-powered debugging assistant for code analysis and error resolution"""
    
    def __init__(self, model_name: str = "gemini-2.5-pro-exp-03-25"):
        self.model_name = model_name
        self.debug_sessions: Dict[str, DebugSession] = {}
        self.error_patterns = self._load_error_patterns()
        self.common_fixes = self._load_common_fixes()
        
    def _load_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load common error patterns and their characteristics"""
        return {
            "SyntaxError": {
                "severity": "high",
                "common_causes": ["missing parentheses", "incorrect indentation", "missing colon"],
                "quick_fixes": ["check syntax", "verify indentation", "check for missing punctuation"]
            },
            "NameError": {
                "severity": "medium",
                "common_causes": ["undefined variable", "typo in variable name", "scope issues"],
                "quick_fixes": ["define variable", "check spelling", "verify variable scope"]
            },
            "TypeError": {
                "severity": "medium",
                "common_causes": ["wrong data type", "incompatible operations", "missing arguments"],
                "quick_fixes": ["check data types", "verify function arguments", "add type conversion"]
            },
            "AttributeError": {
                "severity": "medium",
                "common_causes": ["method doesn't exist", "wrong object type", "None object"],
                "quick_fixes": ["check object type", "verify method name", "add null checks"]
            },
            "ImportError": {
                "severity": "high",
                "common_causes": ["missing module", "incorrect import path", "dependency issues"],
                "quick_fixes": ["install missing package", "check import path", "verify dependencies"]
            },
            "IndexError": {
                "severity": "medium",
                "common_causes": ["list index out of range", "empty list access"],
                "quick_fixes": ["check list length", "add bounds checking", "verify list contents"]
            },
            "KeyError": {
                "severity": "medium",
                "common_causes": ["missing dictionary key", "typo in key name"],
                "quick_fixes": ["check key existence", "use get() method", "verify key spelling"]
            },
            "FileNotFoundError": {
                "severity": "medium",
                "common_causes": ["incorrect file path", "file doesn't exist", "permission issues"],
                "quick_fixes": ["verify file path", "check file existence", "check permissions"]
            }
        }
    
    def _load_common_fixes(self) -> Dict[str, List[str]]:
        """Load common fix patterns for different error types"""
        return {
            "missing_import": [
                "Add import statement at the top of the file",
                "Install required package using pip",
                "Check if module name is correct"
            ],
            "indentation": [
                "Fix indentation to match Python standards (4 spaces)",
                "Ensure consistent indentation throughout the block",
                "Check for mixed tabs and spaces"
            ],
            "syntax": [
                "Add missing parentheses or brackets",
                "Check for missing colons after if/for/while statements",
                "Verify string quotes are properly closed"
            ],
            "type_mismatch": [
                "Add type conversion (str(), int(), float())",
                "Check variable types before operations",
                "Use isinstance() for type checking"
            ]
        }
    
    async def analyze_error(self, error_text: str, code_context: str = "", 
                           file_path: str = "") -> DebugSession:
        """Analyze an error and create a debug session"""
        
        # Parse error information
        error_info = self._parse_error_text(error_text, code_context, file_path)
        
        # Create debug session
        session_id = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session = DebugSession(
            session_id=session_id,
            started_at=datetime.now(),
            error_info=error_info
        )
        
        # Generate suggestions
        suggestions = await self._generate_debug_suggestions(error_info, code_context)
        session.suggestions = suggestions
        
        # Store session
        self.debug_sessions[session_id] = session
        
        return session
    
    def _parse_error_text(self, error_text: str, code_context: str = "", 
                         file_path: str = "") -> ErrorInfo:
        """Parse error text to extract structured information"""
        
        lines = error_text.strip().split('\n')
        
        # Initialize error info
        error_info = ErrorInfo(
            error_type="UnknownError",
            error_message="Unknown error occurred"
        )
        
        # Extract stack trace
        stack_trace = []
        in_traceback = False
        
        for line in lines:
            if line.strip().startswith('Traceback'):
                in_traceback = True
                continue
            
            if in_traceback:
                stack_trace.append(line)
                
                # Extract file and line info
                file_match = re.search(r'File "([^"]+)", line (\d+)', line)
                if file_match:
                    error_info.file_path = file_match.group(1)
                    error_info.line_number = int(file_match.group(2))
        
        # Extract error type and message from last line
        if lines:
            last_line = lines[-1].strip()
            error_match = re.match(r'(\w+Error?): (.+)', last_line)
            if error_match:
                error_info.error_type = error_match.group(1)
                error_info.error_message = error_match.group(2)
            else:
                # Try to extract just the error type
                if ':' in last_line:
                    parts = last_line.split(':', 1)
                    error_info.error_type = parts[0].strip()
                    error_info.error_message = parts[1].strip()
                else:
                    error_info.error_message = last_line
        
        error_info.stack_trace = stack_trace
        
        # Set severity based on error type
        if error_info.error_type in self.error_patterns:
            error_info.severity = self.error_patterns[error_info.error_type]["severity"]
        
        # Extract context lines if available
        if code_context:
            error_info.context_lines = code_context.split('\n')
        
        return error_info
    
    async def _generate_debug_suggestions(self, error_info: ErrorInfo, 
                                        code_context: str = "") -> List[DebugSuggestion]:
        """Generate debugging suggestions using AI and pattern matching"""
        
        suggestions = []
        
        # Add pattern-based suggestions
        pattern_suggestions = self._get_pattern_based_suggestions(error_info)
        suggestions.extend(pattern_suggestions)
        
        # Generate AI-powered suggestions
        ai_suggestions = await self._get_ai_suggestions(error_info, code_context)
        suggestions.extend(ai_suggestions)
        
        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _get_pattern_based_suggestions(self, error_info: ErrorInfo) -> List[DebugSuggestion]:
        """Generate suggestions based on known error patterns"""
        
        suggestions = []
        
        if error_info.error_type in self.error_patterns:
            pattern = self.error_patterns[error_info.error_type]
            
            for i, cause in enumerate(pattern["common_causes"]):
                suggestion = DebugSuggestion(
                    suggestion_id=f"pattern_{error_info.error_type}_{i}",
                    title=f"Fix {cause}",
                    description=pattern["quick_fixes"][i] if i < len(pattern["quick_fixes"]) else cause,
                    fix_type="code_change",
                    confidence=0.7,
                    explanation=f"This is a common cause of {error_info.error_type} errors."
                )
                suggestions.append(suggestion)
        
        # Specific pattern matching
        if error_info.error_type == "ImportError" or "No module named" in error_info.error_message:
            module_match = re.search(r"No module named '([^']+)'", error_info.error_message)
            if module_match:
                module_name = module_match.group(1)
                suggestion = DebugSuggestion(
                    suggestion_id=f"install_{module_name}",
                    title=f"Install missing module: {module_name}",
                    description=f"Install the required module using pip",
                    fix_type="dependency",
                    confidence=0.9,
                    code_changes=[{
                        "type": "command",
                        "command": f"pip install {module_name}",
                        "description": f"Install {module_name} package"
                    }],
                    explanation=f"The module '{module_name}' is not installed in your environment."
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    async def _get_ai_suggestions(self, error_info: ErrorInfo, code_context: str = "") -> List[DebugSuggestion]:
        """Generate AI-powered debugging suggestions"""
        
        context_info = {
            "error_type": error_info.error_type,
            "error_message": error_info.error_message,
            "file_path": error_info.file_path,
            "line_number": error_info.line_number,
            "stack_trace": error_info.stack_trace[-5:] if error_info.stack_trace else [],  # Last 5 lines
            "code_context": code_context[:1000] if code_context else ""  # First 1000 chars
        }
        
        prompt = f"""
        Analyze the following error and provide debugging suggestions:
        
        Error Information:
        {json.dumps(context_info, indent=2)}
        
        Please provide 3-5 specific debugging suggestions in JSON format:
        {{
            "suggestions": [
                {{
                    "title": "Suggestion title",
                    "description": "Detailed description of what to do",
                    "fix_type": "code_change|configuration|dependency|environment",
                    "confidence": 0.8,
                    "code_changes": [
                        {{
                            "type": "replace|insert|delete|command",
                            "file": "file_path",
                            "line": 10,
                            "old_code": "old code",
                            "new_code": "new code",
                            "description": "What this change does"
                        }}
                    ],
                    "explanation": "Why this fix should work",
                    "estimated_time": "2-5 minutes"
                }}
            ]
        }}
        
        Focus on:
        1. Most likely causes of this specific error
        2. Actionable fixes with specific code changes
        3. Best practices to prevent similar errors
        4. Alternative approaches if the main fix doesn't work
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            
            ai_response = json.loads(response.text.strip())
            suggestions = []
            
            for i, sugg_data in enumerate(ai_response.get("suggestions", [])):
                suggestion = DebugSuggestion(
                    suggestion_id=f"ai_{i}",
                    title=sugg_data.get("title", "AI Suggestion"),
                    description=sugg_data.get("description", ""),
                    fix_type=sugg_data.get("fix_type", "code_change"),
                    confidence=sugg_data.get("confidence", 0.5),
                    code_changes=sugg_data.get("code_changes", []),
                    explanation=sugg_data.get("explanation", ""),
                    estimated_time=sugg_data.get("estimated_time", "5-10 minutes")
                )
                suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            print(f"AI suggestion generation failed: {e}")
            return []
    
    async def analyze_stack_trace(self, stack_trace: str) -> Dict[str, Any]:
        """Analyze a stack trace to identify the root cause"""
        
        analysis_prompt = f"""
        Analyze the following stack trace and identify the root cause of the error:
        
        Stack Trace:
        {stack_trace}
        
        Please provide a JSON response with:
        {{
            "root_cause": "Description of the root cause",
            "error_location": {{
                "file": "file_path",
                "line": 123,
                "function": "function_name"
            }},
            "call_chain": ["function1", "function2", "function3"],
            "likely_issues": ["issue1", "issue2", "issue3"],
            "debugging_steps": [
                "Step 1: Check this",
                "Step 2: Verify that",
                "Step 3: Test this"
            ],
            "severity": "low|medium|high|critical"
        }}
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(analysis_prompt)
            
            analysis = json.loads(response.text.strip())
            return analysis
            
        except Exception as e:
            return {
                "root_cause": "Unable to analyze stack trace",
                "error": str(e)
            }
    
    def apply_suggestion(self, session_id: str, suggestion_id: str, 
                        auto_apply: bool = False) -> Dict[str, Any]:
        """Apply a debugging suggestion"""
        
        if session_id not in self.debug_sessions:
            return {"error": "Debug session not found"}
        
        session = self.debug_sessions[session_id]
        suggestion = None
        
        for sugg in session.suggestions:
            if sugg.suggestion_id == suggestion_id:
                suggestion = sugg
                break
        
        if not suggestion:
            return {"error": "Suggestion not found"}
        
        results = []
        
        try:
            for change in suggestion.code_changes:
                if change["type"] == "command":
                    if auto_apply:
                        result = subprocess.run(
                            change["command"].split(),
                            capture_output=True,
                            text=True
                        )
                        results.append({
                            "type": "command",
                            "command": change["command"],
                            "success": result.returncode == 0,
                            "output": result.stdout,
                            "error": result.stderr
                        })
                    else:
                        results.append({
                            "type": "command",
                            "command": change["command"],
                            "message": "Command ready to execute (use auto_apply=True to run)"
                        })
                
                elif change["type"] in ["replace", "insert", "delete"]:
                    if auto_apply and "file" in change:
                        file_result = self._apply_file_change(change)
                        results.append(file_result)
                    else:
                        results.append({
                            "type": change["type"],
                            "change": change,
                            "message": "File change ready to apply"
                        })
            
            # Mark suggestion as applied
            if auto_apply:
                session.applied_fixes.append(suggestion_id)
            
            return {
                "success": True,
                "suggestion": suggestion.title,
                "results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _apply_file_change(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a file change"""
        
        try:
            file_path = Path(change["file"])
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            # Read current file content
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            if change["type"] == "replace":
                line_num = change.get("line", 1) - 1  # Convert to 0-based index
                if 0 <= line_num < len(lines):
                    old_line = lines[line_num].rstrip()
                    if change.get("old_code", "").strip() in old_line:
                        lines[line_num] = change["new_code"] + "\n"
                        
                        # Write back to file
                        with open(file_path, 'w') as f:
                            f.writelines(lines)
                        
                        return {
                            "success": True,
                            "type": "replace",
                            "file": str(file_path),
                            "line": line_num + 1,
                            "old_code": old_line,
                            "new_code": change["new_code"]
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Old code not found at specified line"
                        }
                else:
                    return {
                        "success": False,
                        "error": "Line number out of range"
                    }
            
            elif change["type"] == "insert":
                line_num = change.get("line", len(lines))
                lines.insert(line_num, change["new_code"] + "\n")
                
                with open(file_path, 'w') as f:
                    f.writelines(lines)
                
                return {
                    "success": True,
                    "type": "insert",
                    "file": str(file_path),
                    "line": line_num + 1,
                    "new_code": change["new_code"]
                }
            
            elif change["type"] == "delete":
                line_num = change.get("line", 1) - 1
                if 0 <= line_num < len(lines):
                    deleted_line = lines.pop(line_num)
                    
                    with open(file_path, 'w') as f:
                        f.writelines(lines)
                    
                    return {
                        "success": True,
                        "type": "delete",
                        "file": str(file_path),
                        "line": line_num + 1,
                        "deleted_code": deleted_line.rstrip()
                    }
                else:
                    return {
                        "success": False,
                        "error": "Line number out of range"
                    }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_debug_session(self, session_id: str) -> Optional[DebugSession]:
        """Get a debug session by ID"""
        return self.debug_sessions.get(session_id)
    
    def list_debug_sessions(self) -> List[Dict[str, Any]]:
        """List all debug sessions"""
        return [
            {
                "session_id": session.session_id,
                "started_at": session.started_at.isoformat(),
                "error_type": session.error_info.error_type,
                "error_message": session.error_info.error_message[:100] + "..." if len(session.error_info.error_message) > 100 else session.error_info.error_message,
                "status": session.status,
                "suggestions_count": len(session.suggestions),
                "applied_fixes": len(session.applied_fixes)
            }
            for session in self.debug_sessions.values()
        ]
    
    def resolve_session(self, session_id: str, resolution_notes: str = "") -> bool:
        """Mark a debug session as resolved"""
        if session_id in self.debug_sessions:
            session = self.debug_sessions[session_id]
            session.status = "resolved"
            session.resolution_notes = resolution_notes
            return True
        return False
    
    async def explain_error(self, error_text: str) -> str:
        """Provide a detailed explanation of an error"""
        
        explanation_prompt = f"""
        Explain the following error in simple terms that a developer can understand:
        
        Error: {error_text}
        
        Please provide:
        1. What this error means
        2. Why it typically occurs
        3. How to prevent it in the future
        4. Common scenarios where this error happens
        
        Keep the explanation clear and practical.
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(explanation_prompt)
            return response.text.strip()
        except Exception as e:
            return f"Unable to explain error: {str(e)}"

# Global debugging assistant instance
debugging_assistant = DebuggingAssistant()
