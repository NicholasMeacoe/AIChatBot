from features.plugins import PluginBase
import requests

class ExamplePlugin(PluginBase):
    def get_name(self):
        return "example"
    
    def get_description(self):
        return "Example plugin demonstrating the plugin system"
    
    def execute(self, action, **kwargs):
        if action == "hello":
            return {"message": f"Hello from plugin! Args: {kwargs}"}
        elif action == "weather":
            # Example weather API call (placeholder)
            city = kwargs.get('city', 'London')
            return {"weather": f"Weather in {city}: Sunny, 22°C"}
        return {"error": "Unknown action"}