import json
import os
from datetime import datetime

class TemplateManager:
    def __init__(self, templates_dir="templates_data"):
        self.templates_dir = templates_dir
        os.makedirs(templates_dir, exist_ok=True)
        self.templates_file = os.path.join(templates_dir, "templates.json")
        self.load_templates()
    
    def load_templates(self):
        """Load templates from file"""
        if os.path.exists(self.templates_file):
            with open(self.templates_file, 'r') as f:
                self.templates = json.load(f)
        else:
            self.templates = self._get_default_templates()
            self.save_templates()
    
    def save_templates(self):
        """Save templates to file"""
        with open(self.templates_file, 'w') as f:
            json.dump(self.templates, f, indent=2)
    
    def _get_default_templates(self):
        return {
            "code_review": {
                "name": "Code Review",
                "category": "Development",
                "template": "Please review this code for:\n1. Best practices\n2. Security issues\n3. Performance optimizations\n4. Code clarity\n\n{code_context}",
                "variables": ["code_context"]
            },
            "document_summary": {
                "name": "Document Summary",
                "category": "Analysis",
                "template": "Please provide a comprehensive summary of the following document:\n\n{document_content}\n\nFocus on:\n- Key points\n- Main conclusions\n- Action items",
                "variables": ["document_content"]
            },
            "creative_writing": {
                "name": "Creative Writing",
                "category": "Creative",
                "template": "Write a {style} story about {topic} with the following elements:\n- Setting: {setting}\n- Main character: {character}\n- Conflict: {conflict}",
                "variables": ["style", "topic", "setting", "character", "conflict"]
            }
        }
    
    def get_templates(self, category=None):
        """Get all templates or by category"""
        if category:
            return {k: v for k, v in self.templates.items() if v.get('category') == category}
        return self.templates
    
    def add_template(self, template_id, name, category, template, variables):
        """Add new template"""
        self.templates[template_id] = {
            "name": name,
            "category": category,
            "template": template,
            "variables": variables,
            "created": datetime.now().isoformat()
        }
        self.save_templates()
    
    def apply_template(self, template_id, variables_dict):
        """Apply variables to template"""
        if template_id not in self.templates:
            return None
        
        template = self.templates[template_id]["template"]
        try:
            return template.format(**variables_dict)
        except KeyError as e:
            return f"Missing variable: {e}"