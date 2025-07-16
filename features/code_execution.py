import subprocess
import tempfile
import os
import json
import sys
from datetime import datetime

class CodeExecutor:
    def __init__(self):
        self.supported_languages = {
            'python': {'extension': '.py', 'command': [sys.executable]},
            'javascript': {'extension': '.js', 'command': ['node']},
            'bash': {'extension': '.sh', 'command': ['bash']},
        }
        self.execution_timeout = 30  # seconds
    
    def execute_code(self, code, language='python', context_files=None):
        """Execute code in sandboxed environment"""
        if language not in self.supported_languages:
            return {'error': f'Unsupported language: {language}'}
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create code file
                lang_config = self.supported_languages[language]
                code_file = os.path.join(temp_dir, f'code{lang_config["extension"]}')
                
                with open(code_file, 'w') as f:
                    f.write(code)
                
                # Copy context files if provided
                if context_files:
                    for file_path in context_files:
                        if os.path.exists(file_path):
                            dest_path = os.path.join(temp_dir, os.path.basename(file_path))
                            with open(file_path, 'r') as src, open(dest_path, 'w') as dst:
                                dst.write(src.read())
                
                # Execute code
                cmd = lang_config['command'] + [code_file]
                result = subprocess.run(
                    cmd,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.execution_timeout
                )
                
                return {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode,
                    'execution_time': datetime.now().isoformat()
                }
                
        except subprocess.TimeoutExpired:
            return {'error': f'Code execution timed out after {self.execution_timeout} seconds'}
        except Exception as e:
            return {'error': f'Execution error: {str(e)}'}
    
    def create_notebook_cell(self, code, language='python'):
        """Create Jupyter notebook cell format"""
        return {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': code.split('\n')
        }
    
    def extract_code_blocks(self, text):
        """Extract code blocks from markdown text"""
        import re
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        code_blocks = []
        for lang, code in matches:
            code_blocks.append({
                'language': lang or 'python',
                'code': code.strip()
            })
        
        return code_blocks