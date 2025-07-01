import importlib.util
import os
import json
from abc import ABC, abstractmethod

class PluginBase(ABC):
    """Base class for all plugins"""
    
    @abstractmethod
    def get_name(self):
        pass
    
    @abstractmethod
    def get_description(self):
        pass
    
    @abstractmethod
    def execute(self, *args, **kwargs):
        pass

class PluginManager:
    def __init__(self, plugins_dir="plugins"):
        self.plugins_dir = plugins_dir
        self.plugins = {}
        self.load_plugins()
    
    def load_plugins(self):
        """Load all plugins from plugins directory"""
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            return
        
        for filename in os.listdir(self.plugins_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                plugin_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(
                        plugin_name, 
                        os.path.join(self.plugins_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find plugin class
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, PluginBase) and 
                            attr != PluginBase):
                            plugin_instance = attr()
                            self.plugins[plugin_instance.get_name()] = plugin_instance
                            break
                            
                except Exception as e:
                    print(f"Error loading plugin {plugin_name}: {e}")
    
    def get_plugin(self, name):
        """Get plugin by name"""
        return self.plugins.get(name)
    
    def list_plugins(self):
        """List all available plugins"""
        return {name: plugin.get_description() for name, plugin in self.plugins.items()}
    
    def execute_plugin(self, name, *args, **kwargs):
        """Execute plugin by name"""
        plugin = self.get_plugin(name)
        if plugin:
            return plugin.execute(*args, **kwargs)
        return {'error': f'Plugin {name} not found'}

# Example plugins
class GitHubPlugin(PluginBase):
    def get_name(self):
        return "github"
    
    def get_description(self):
        return "GitHub integration for repository information"
    
    def execute(self, action, repo=None, **kwargs):
        # Placeholder for GitHub API integration
        if action == "get_repo_info":
            return {"repo": repo, "info": "Repository information placeholder"}
        return {"error": "Unknown action"}

class SlackPlugin(PluginBase):
    def get_name(self):
        return "slack"
    
    def get_description(self):
        return "Slack integration for sending messages"
    
    def execute(self, action, message=None, channel=None, **kwargs):
        # Placeholder for Slack API integration
        if action == "send_message":
            return {"status": "Message sent", "channel": channel, "message": message}
        return {"error": "Unknown action"}