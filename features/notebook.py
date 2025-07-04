"""
Interactive Code Notebooks & Data Visualization Feature
Transforms the chat into an interactive notebook-like environment with automatic data visualization.
"""

import json
import io
import sys
import traceback
import base64
from contextlib import redirect_stdout, redirect_stderr
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
import seaborn as sns
from typing import Dict, Any, List, Optional, Tuple
import re
import ast
import inspect

class NotebookManager:
    """Manages interactive code execution and data visualization"""
    
    def __init__(self):
        self.execution_context = {}
        self.execution_history = []
        self.output_handlers = {
            'matplotlib': self._handle_matplotlib_output,
            'plotly': self._handle_plotly_output,
            'pandas': self._handle_pandas_output,
            'numpy': self._handle_numpy_output,
            'seaborn': self._handle_seaborn_output
        }
        
    def execute_code(self, code: str, cell_id: str = None) -> Dict[str, Any]:
        """Execute code and capture output with automatic visualization detection"""
        result = {
            'cell_id': cell_id or f"cell_{len(self.execution_history)}",
            'code': code,
            'output': '',
            'error': None,
            'visualizations': [],
            'data_summary': None,
            'execution_time': 0
        }
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            import time
            start_time = time.time()
            
            # Clear any existing matplotlib figures
            plt.clf()
            
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute the code in the persistent context
                exec(code, self.execution_context)
            
            result['execution_time'] = time.time() - start_time
            result['output'] = stdout_capture.getvalue()
            
            # Check for data visualizations and summaries
            result['visualizations'] = self._detect_and_generate_visualizations()
            result['data_summary'] = self._generate_data_summary()
            
        except Exception as e:
            result['error'] = {
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc()
            }
            result['output'] = stderr_capture.getvalue()
        
        self.execution_history.append(result)
        return result
    
    def _detect_and_generate_visualizations(self) -> List[Dict[str, Any]]:
        """Detect data in context and generate appropriate visualizations"""
        visualizations = []
        
        # Check for matplotlib figures
        if plt.get_fignums():
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                img_buffer = io.BytesIO()
                fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
                img_buffer.seek(0)
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                
                visualizations.append({
                    'type': 'matplotlib',
                    'data': img_base64,
                    'format': 'png'
                })
                plt.close(fig)
        
        # Check for pandas DataFrames
        for var_name, var_value in self.execution_context.items():
            if isinstance(var_value, pd.DataFrame) and not var_name.startswith('_'):
                # Generate automatic visualizations for DataFrames
                df_viz = self._auto_visualize_dataframe(var_value, var_name)
                visualizations.extend(df_viz)
        
        return visualizations
    
    def _auto_visualize_dataframe(self, df: pd.DataFrame, name: str) -> List[Dict[str, Any]]:
        """Automatically generate visualizations for a DataFrame"""
        visualizations = []
        
        if df.empty or len(df) > 10000:  # Skip very large datasets
            return visualizations
        
        # Generate summary table
        html_table = df.head(10).to_html(classes='table table-striped table-hover')
        visualizations.append({
            'type': 'table',
            'data': html_table,
            'title': f'{name} - First 10 rows',
            'format': 'html'
        })
        
        # Generate basic statistics if numeric columns exist
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            stats_df = df[numeric_cols].describe()
            stats_html = stats_df.to_html(classes='table table-striped')
            visualizations.append({
                'type': 'statistics',
                'data': stats_html,
                'title': f'{name} - Statistics',
                'format': 'html'
            })
            
            # Generate correlation heatmap if multiple numeric columns
            if len(numeric_cols) > 1:
                fig = go.Figure(data=go.Heatmap(
                    z=df[numeric_cols].corr().values,
                    x=numeric_cols,
                    y=numeric_cols,
                    colorscale='RdBu',
                    zmid=0
                ))
                fig.update_layout(title=f'{name} - Correlation Matrix')
                
                visualizations.append({
                    'type': 'plotly',
                    'data': pio.to_json(fig),
                    'title': f'{name} - Correlation Matrix',
                    'format': 'json'
                })
        
        # Generate distribution plots for numeric columns
        for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
            if df[col].nunique() > 1:  # Only if there's variation
                fig = px.histogram(df, x=col, title=f'{name} - {col} Distribution')
                visualizations.append({
                    'type': 'plotly',
                    'data': pio.to_json(fig),
                    'title': f'{name} - {col} Distribution',
                    'format': 'json'
                })
        
        return visualizations
    
    def _generate_data_summary(self) -> Optional[Dict[str, Any]]:
        """Generate a summary of data objects in the execution context"""
        summary = {
            'dataframes': {},
            'arrays': {},
            'variables': {}
        }
        
        for var_name, var_value in self.execution_context.items():
            if var_name.startswith('_'):
                continue
                
            if isinstance(var_value, pd.DataFrame):
                summary['dataframes'][var_name] = {
                    'shape': var_value.shape,
                    'columns': list(var_value.columns),
                    'dtypes': var_value.dtypes.to_dict(),
                    'memory_usage': var_value.memory_usage(deep=True).sum()
                }
            elif isinstance(var_value, np.ndarray):
                summary['arrays'][var_name] = {
                    'shape': var_value.shape,
                    'dtype': str(var_value.dtype),
                    'size': var_value.size
                }
            elif isinstance(var_value, (int, float, str, list, dict)):
                summary['variables'][var_name] = {
                    'type': type(var_value).__name__,
                    'value': str(var_value)[:100] + ('...' if len(str(var_value)) > 100 else '')
                }
        
        return summary if any(summary.values()) else None
    
    def _handle_matplotlib_output(self, fig):
        """Handle matplotlib figure output"""
        pass  # Already handled in _detect_and_generate_visualizations
    
    def _handle_plotly_output(self, fig):
        """Handle plotly figure output"""
        pass  # Already handled in _detect_and_generate_visualizations
    
    def _handle_pandas_output(self, df):
        """Handle pandas DataFrame output"""
        pass  # Already handled in _detect_and_generate_visualizations
    
    def _handle_numpy_output(self, arr):
        """Handle numpy array output"""
        pass  # Already handled in _detect_and_generate_visualizations
    
    def _handle_seaborn_output(self, plot):
        """Handle seaborn plot output"""
        pass  # Already handled in _detect_and_generate_visualizations
    
    def get_context_variables(self) -> Dict[str, str]:
        """Get a summary of variables in the execution context"""
        variables = {}
        for var_name, var_value in self.execution_context.items():
            if not var_name.startswith('_'):
                variables[var_name] = f"{type(var_value).__name__}: {str(var_value)[:50]}..."
        return variables
    
    def clear_context(self):
        """Clear the execution context"""
        # Keep built-in modules and functions
        builtins_to_keep = {k: v for k, v in self.execution_context.items() 
                           if k.startswith('__') or k in ['pd', 'np', 'plt', 'px', 'go']}
        self.execution_context.clear()
        self.execution_context.update(builtins_to_keep)
        
        # Re-import common libraries
        self.execution_context.update({
            'pd': pd,
            'np': np,
            'plt': plt,
            'px': px,
            'go': go,
            'sns': sns
        })
    
    def export_notebook(self, format='json') -> str:
        """Export the notebook in various formats"""
        if format == 'json':
            return json.dumps({
                'cells': self.execution_history,
                'metadata': {
                    'kernelspec': {
                        'display_name': 'Python 3',
                        'language': 'python',
                        'name': 'python3'
                    }
                }
            }, indent=2)
        
        # Add other export formats as needed
        return ""

# Global notebook manager instance
notebook_manager = NotebookManager()
