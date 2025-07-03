"""
Collaborative Whiteboard & Diagramming Feature
Provides real-time collaborative whiteboard with AI-generated diagrams and visual problem-solving.
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import google.generativeai as genai
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import networkx as nx
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import numpy as np

class ElementType(Enum):
    TEXT = "text"
    SHAPE = "shape"
    LINE = "line"
    ARROW = "arrow"
    IMAGE = "image"
    DIAGRAM = "diagram"
    STICKY_NOTE = "sticky_note"
    FLOWCHART = "flowchart"
    MINDMAP = "mindmap"

class ShapeType(Enum):
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    TRIANGLE = "triangle"
    DIAMOND = "diamond"
    HEXAGON = "hexagon"
    CLOUD = "cloud"
    STAR = "star"

@dataclass
class Point:
    x: float
    y: float

@dataclass
class WhiteboardElement:
    id: str
    element_type: ElementType
    position: Point
    width: float = 100
    height: float = 50
    content: str = ""
    style: Dict[str, Any] = field(default_factory=dict)
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    z_index: int = 0
    locked: bool = False
    
    # Shape-specific properties
    shape_type: Optional[ShapeType] = None
    
    # Line/Arrow specific properties
    start_point: Optional[Point] = None
    end_point: Optional[Point] = None
    
    # Connection properties
    connected_to: List[str] = field(default_factory=list)
    connection_points: List[Point] = field(default_factory=list)

@dataclass
class Whiteboard:
    id: str
    name: str
    description: str = ""
    width: float = 1920
    height: float = 1080
    background_color: str = "#ffffff"
    elements: Dict[str, WhiteboardElement] = field(default_factory=dict)
    collaborators: Set[str] = field(default_factory=set)
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    
    # Grid and snap settings
    grid_enabled: bool = True
    grid_size: int = 20
    snap_to_grid: bool = True

@dataclass
class DiagramTemplate:
    name: str
    description: str
    template_type: str  # flowchart, mindmap, architecture, sequence, etc.
    elements: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    layout_hints: Dict[str, Any] = field(default_factory=dict)

class CollaborativeWhiteboardManager:
    """Manages collaborative whiteboards and AI-generated diagrams"""
    
    def __init__(self, model_name: str = "gemini-2.5-pro-exp-03-25"):
        self.model_name = model_name
        self.whiteboards: Dict[str, Whiteboard] = {}
        self.templates: Dict[str, DiagramTemplate] = {}
        self.active_sessions: Dict[str, Set[str]] = {}  # whiteboard_id -> user_ids
        
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize common diagram templates"""
        
        # Flowchart template
        flowchart_template = DiagramTemplate(
            name="Basic Flowchart",
            description="Standard flowchart with start, process, decision, and end nodes",
            template_type="flowchart",
            elements=[
                {"type": "start", "shape": "circle", "label": "Start"},
                {"type": "process", "shape": "rectangle", "label": "Process"},
                {"type": "decision", "shape": "diamond", "label": "Decision?"},
                {"type": "end", "shape": "circle", "label": "End"}
            ],
            connections=[
                {"from": "start", "to": "process"},
                {"from": "process", "to": "decision"},
                {"from": "decision", "to": "end", "label": "Yes"},
                {"from": "decision", "to": "process", "label": "No"}
            ]
        )
        
        # Mind map template
        mindmap_template = DiagramTemplate(
            name="Mind Map",
            description="Hierarchical mind map structure",
            template_type="mindmap",
            elements=[
                {"type": "central", "shape": "circle", "label": "Central Topic"},
                {"type": "branch", "shape": "rectangle", "label": "Main Branch"},
                {"type": "leaf", "shape": "rectangle", "label": "Sub Topic"}
            ],
            connections=[
                {"from": "central", "to": "branch"},
                {"from": "branch", "to": "leaf"}
            ]
        )
        
        # System architecture template
        architecture_template = DiagramTemplate(
            name="System Architecture",
            description="Basic system architecture diagram",
            template_type="architecture",
            elements=[
                {"type": "user", "shape": "rectangle", "label": "User"},
                {"type": "frontend", "shape": "rectangle", "label": "Frontend"},
                {"type": "backend", "shape": "rectangle", "label": "Backend"},
                {"type": "database", "shape": "cylinder", "label": "Database"}
            ],
            connections=[
                {"from": "user", "to": "frontend"},
                {"from": "frontend", "to": "backend"},
                {"from": "backend", "to": "database"}
            ]
        )
        
        self.templates["flowchart"] = flowchart_template
        self.templates["mindmap"] = mindmap_template
        self.templates["architecture"] = architecture_template
    
    def create_whiteboard(self, name: str, description: str = "", 
                         created_by: str = "system", 
                         width: float = 1920, height: float = 1080) -> str:
        """Create a new whiteboard"""
        
        whiteboard_id = str(uuid.uuid4())
        
        whiteboard = Whiteboard(
            id=whiteboard_id,
            name=name,
            description=description,
            width=width,
            height=height,
            created_by=created_by
        )
        
        whiteboard.collaborators.add(created_by)
        self.whiteboards[whiteboard_id] = whiteboard
        self.active_sessions[whiteboard_id] = {created_by}
        
        return whiteboard_id
    
    def add_element(self, whiteboard_id: str, element_type: ElementType, 
                   position: Point, content: str = "", 
                   style: Dict[str, Any] = None, 
                   created_by: str = "system") -> str:
        """Add an element to the whiteboard"""
        
        if whiteboard_id not in self.whiteboards:
            raise ValueError("Whiteboard not found")
        
        element_id = str(uuid.uuid4())
        style = style or {}
        
        # Set default styles based on element type
        default_styles = {
            ElementType.TEXT: {"font_size": 14, "color": "#000000", "font_family": "Arial"},
            ElementType.SHAPE: {"fill_color": "#e1f5fe", "border_color": "#01579b", "border_width": 2},
            ElementType.STICKY_NOTE: {"fill_color": "#fff59d", "border_color": "#f57f17", "border_width": 1},
            ElementType.LINE: {"color": "#000000", "width": 2},
            ElementType.ARROW: {"color": "#000000", "width": 2, "arrow_size": 10}
        }
        
        if element_type in default_styles:
            merged_style = default_styles[element_type].copy()
            merged_style.update(style)
            style = merged_style
        
        element = WhiteboardElement(
            id=element_id,
            element_type=element_type,
            position=position,
            content=content,
            style=style,
            created_by=created_by
        )
        
        whiteboard = self.whiteboards[whiteboard_id]
        whiteboard.elements[element_id] = element
        whiteboard.updated_at = datetime.now()
        whiteboard.version += 1
        
        return element_id
    
    def update_element(self, whiteboard_id: str, element_id: str, 
                      updates: Dict[str, Any], updated_by: str = "system") -> bool:
        """Update an existing element"""
        
        if whiteboard_id not in self.whiteboards:
            return False
        
        whiteboard = self.whiteboards[whiteboard_id]
        
        if element_id not in whiteboard.elements:
            return False
        
        element = whiteboard.elements[element_id]
        
        if element.locked:
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(element, key):
                setattr(element, key, value)
        
        element.updated_at = datetime.now()
        whiteboard.updated_at = datetime.now()
        whiteboard.version += 1
        
        return True
    
    def delete_element(self, whiteboard_id: str, element_id: str) -> bool:
        """Delete an element from the whiteboard"""
        
        if whiteboard_id not in self.whiteboards:
            return False
        
        whiteboard = self.whiteboards[whiteboard_id]
        
        if element_id not in whiteboard.elements:
            return False
        
        element = whiteboard.elements[element_id]
        
        if element.locked:
            return False
        
        # Remove connections to this element
        for other_element in whiteboard.elements.values():
            if element_id in other_element.connected_to:
                other_element.connected_to.remove(element_id)
        
        del whiteboard.elements[element_id]
        whiteboard.updated_at = datetime.now()
        whiteboard.version += 1
        
        return True
    
    def connect_elements(self, whiteboard_id: str, from_element_id: str, 
                        to_element_id: str, connection_style: Dict[str, Any] = None) -> str:
        """Create a connection between two elements"""
        
        if whiteboard_id not in self.whiteboards:
            raise ValueError("Whiteboard not found")
        
        whiteboard = self.whiteboards[whiteboard_id]
        
        if from_element_id not in whiteboard.elements or to_element_id not in whiteboard.elements:
            raise ValueError("One or both elements not found")
        
        from_element = whiteboard.elements[from_element_id]
        to_element = whiteboard.elements[to_element_id]
        
        # Calculate connection points
        from_point = Point(
            from_element.position.x + from_element.width / 2,
            from_element.position.y + from_element.height / 2
        )
        to_point = Point(
            to_element.position.x + to_element.width / 2,
            to_element.position.y + to_element.height / 2
        )
        
        # Create connection element
        connection_style = connection_style or {"color": "#666666", "width": 2}
        
        connection_id = self.add_element(
            whiteboard_id,
            ElementType.ARROW,
            from_point,
            style=connection_style
        )
        
        connection = whiteboard.elements[connection_id]
        connection.start_point = from_point
        connection.end_point = to_point
        
        # Update element connections
        from_element.connected_to.append(to_element_id)
        
        return connection_id
    
    async def generate_diagram_from_description(self, description: str, 
                                              diagram_type: str = "auto") -> Dict[str, Any]:
        """Generate a diagram based on natural language description"""
        
        generation_prompt = f"""
        Create a diagram based on the following description:
        
        Description: {description}
        Diagram Type: {diagram_type}
        
        Generate a JSON structure for the diagram with the following format:
        {{
            "diagram_type": "flowchart|mindmap|architecture|sequence|other",
            "title": "Diagram title",
            "elements": [
                {{
                    "id": "unique_id",
                    "type": "shape|text",
                    "shape": "rectangle|circle|diamond|triangle",
                    "label": "Element label",
                    "position": {{"x": 100, "y": 100}},
                    "size": {{"width": 120, "height": 60}},
                    "style": {{"fill_color": "#e1f5fe", "border_color": "#01579b"}}
                }}
            ],
            "connections": [
                {{
                    "from": "element_id_1",
                    "to": "element_id_2",
                    "label": "Connection label (optional)",
                    "style": {{"color": "#666666", "width": 2}}
                }}
            ],
            "layout": {{"type": "hierarchical|circular|grid", "spacing": 150}}
        }}
        
        Guidelines:
        - Use appropriate shapes for different element types
        - Position elements to avoid overlaps
        - Use consistent styling
        - Include meaningful labels
        - Create logical connections between related elements
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(generation_prompt)
            
            diagram_spec = json.loads(response.text.strip())
            return diagram_spec
            
        except Exception as e:
            return {"error": f"Failed to generate diagram: {str(e)}"}
    
    async def create_diagram_from_description(self, whiteboard_id: str, 
                                            description: str, 
                                            diagram_type: str = "auto",
                                            position: Point = None) -> Dict[str, Any]:
        """Create a diagram on the whiteboard from description"""
        
        if whiteboard_id not in self.whiteboards:
            return {"error": "Whiteboard not found"}
        
        # Generate diagram specification
        diagram_spec = await self.generate_diagram_from_description(description, diagram_type)
        
        if "error" in diagram_spec:
            return diagram_spec
        
        position = position or Point(100, 100)
        created_elements = []
        created_connections = []
        
        try:
            # Create elements
            for element_spec in diagram_spec.get("elements", []):
                element_position = Point(
                    position.x + element_spec["position"]["x"],
                    position.y + element_spec["position"]["y"]
                )
                
                element_id = self.add_element(
                    whiteboard_id,
                    ElementType.SHAPE if element_spec["type"] == "shape" else ElementType.TEXT,
                    element_position,
                    content=element_spec["label"],
                    style=element_spec.get("style", {})
                )
                
                # Update element properties
                if "size" in element_spec:
                    self.update_element(whiteboard_id, element_id, {
                        "width": element_spec["size"]["width"],
                        "height": element_spec["size"]["height"]
                    })
                
                if "shape" in element_spec:
                    self.update_element(whiteboard_id, element_id, {
                        "shape_type": ShapeType(element_spec["shape"])
                    })
                
                created_elements.append({
                    "id": element_id,
                    "spec_id": element_spec["id"]
                })
            
            # Create connections
            element_id_map = {elem["spec_id"]: elem["id"] for elem in created_elements}
            
            for connection_spec in diagram_spec.get("connections", []):
                from_id = element_id_map.get(connection_spec["from"])
                to_id = element_id_map.get(connection_spec["to"])
                
                if from_id and to_id:
                    connection_id = self.connect_elements(
                        whiteboard_id,
                        from_id,
                        to_id,
                        connection_spec.get("style", {})
                    )
                    created_connections.append(connection_id)
            
            return {
                "success": True,
                "diagram_type": diagram_spec.get("diagram_type", "unknown"),
                "title": diagram_spec.get("title", "Generated Diagram"),
                "elements_created": len(created_elements),
                "connections_created": len(created_connections),
                "element_ids": [elem["id"] for elem in created_elements],
                "connection_ids": created_connections
            }
            
        except Exception as e:
            return {"error": f"Failed to create diagram: {str(e)}"}
    
    def render_whiteboard_to_image(self, whiteboard_id: str, 
                                  format: str = "png") -> Optional[str]:
        """Render the whiteboard to an image and return as base64"""
        
        if whiteboard_id not in self.whiteboards:
            return None
        
        whiteboard = self.whiteboards[whiteboard_id]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(whiteboard.width/100, whiteboard.height/100))
        ax.set_xlim(0, whiteboard.width)
        ax.set_ylim(0, whiteboard.height)
        ax.set_aspect('equal')
        
        # Set background
        ax.set_facecolor(whiteboard.background_color)
        
        # Draw grid if enabled
        if whiteboard.grid_enabled:
            for x in range(0, int(whiteboard.width), whiteboard.grid_size):
                ax.axvline(x, color='#e0e0e0', linewidth=0.5, alpha=0.5)
            for y in range(0, int(whiteboard.height), whiteboard.grid_size):
                ax.axhline(y, color='#e0e0e0', linewidth=0.5, alpha=0.5)
        
        # Sort elements by z-index
        sorted_elements = sorted(whiteboard.elements.values(), key=lambda e: e.z_index)
        
        # Draw elements
        for element in sorted_elements:
            self._draw_element(ax, element)
        
        # Remove axes
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # Save to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format=format, bbox_inches='tight', dpi=150)
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        
        return image_base64
    
    def _draw_element(self, ax, element: WhiteboardElement):
        """Draw a single element on the matplotlib axes"""
        
        if element.element_type == ElementType.SHAPE:
            self._draw_shape(ax, element)
        elif element.element_type == ElementType.TEXT:
            self._draw_text(ax, element)
        elif element.element_type == ElementType.STICKY_NOTE:
            self._draw_sticky_note(ax, element)
        elif element.element_type in [ElementType.LINE, ElementType.ARROW]:
            self._draw_line_or_arrow(ax, element)
    
    def _draw_shape(self, ax, element: WhiteboardElement):
        """Draw a shape element"""
        
        style = element.style
        fill_color = style.get("fill_color", "#e1f5fe")
        border_color = style.get("border_color", "#01579b")
        border_width = style.get("border_width", 2)
        
        if element.shape_type == ShapeType.RECTANGLE:
            rect = FancyBboxPatch(
                (element.position.x, element.position.y),
                element.width, element.height,
                boxstyle="round,pad=5",
                facecolor=fill_color,
                edgecolor=border_color,
                linewidth=border_width
            )
            ax.add_patch(rect)
        
        elif element.shape_type == ShapeType.CIRCLE:
            circle = plt.Circle(
                (element.position.x + element.width/2, element.position.y + element.height/2),
                min(element.width, element.height)/2,
                facecolor=fill_color,
                edgecolor=border_color,
                linewidth=border_width
            )
            ax.add_patch(circle)
        
        elif element.shape_type == ShapeType.DIAMOND:
            diamond_points = [
                [element.position.x + element.width/2, element.position.y + element.height],
                [element.position.x + element.width, element.position.y + element.height/2],
                [element.position.x + element.width/2, element.position.y],
                [element.position.x, element.position.y + element.height/2]
            ]
            diamond = patches.Polygon(
                diamond_points,
                facecolor=fill_color,
                edgecolor=border_color,
                linewidth=border_width
            )
            ax.add_patch(diamond)
        
        # Add text label
        if element.content:
            ax.text(
                element.position.x + element.width/2,
                element.position.y + element.height/2,
                element.content,
                ha='center', va='center',
                fontsize=style.get("font_size", 10),
                color=style.get("text_color", "#000000"),
                wrap=True
            )
    
    def _draw_text(self, ax, element: WhiteboardElement):
        """Draw a text element"""
        
        style = element.style
        ax.text(
            element.position.x,
            element.position.y,
            element.content,
            fontsize=style.get("font_size", 14),
            color=style.get("color", "#000000"),
            fontfamily=style.get("font_family", "Arial"),
            ha='left', va='bottom'
        )
    
    def _draw_sticky_note(self, ax, element: WhiteboardElement):
        """Draw a sticky note element"""
        
        style = element.style
        fill_color = style.get("fill_color", "#fff59d")
        border_color = style.get("border_color", "#f57f17")
        
        # Draw sticky note background
        rect = FancyBboxPatch(
            (element.position.x, element.position.y),
            element.width, element.height,
            boxstyle="round,pad=3",
            facecolor=fill_color,
            edgecolor=border_color,
            linewidth=1
        )
        ax.add_patch(rect)
        
        # Add text
        if element.content:
            ax.text(
                element.position.x + 10,
                element.position.y + element.height - 10,
                element.content,
                ha='left', va='top',
                fontsize=style.get("font_size", 10),
                color=style.get("text_color", "#000000"),
                wrap=True
            )
    
    def _draw_line_or_arrow(self, ax, element: WhiteboardElement):
        """Draw a line or arrow element"""
        
        if not element.start_point or not element.end_point:
            return
        
        style = element.style
        color = style.get("color", "#000000")
        width = style.get("width", 2)
        
        if element.element_type == ElementType.ARROW:
            arrow = patches.FancyArrowPatch(
                (element.start_point.x, element.start_point.y),
                (element.end_point.x, element.end_point.y),
                arrowstyle='->', 
                mutation_scale=style.get("arrow_size", 20),
                color=color,
                linewidth=width
            )
            ax.add_patch(arrow)
        else:
            ax.plot(
                [element.start_point.x, element.end_point.x],
                [element.start_point.y, element.end_point.y],
                color=color,
                linewidth=width
            )
    
    def get_whiteboard_info(self, whiteboard_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a whiteboard"""
        
        if whiteboard_id not in self.whiteboards:
            return None
        
        whiteboard = self.whiteboards[whiteboard_id]
        
        return {
            "id": whiteboard.id,
            "name": whiteboard.name,
            "description": whiteboard.description,
            "width": whiteboard.width,
            "height": whiteboard.height,
            "element_count": len(whiteboard.elements),
            "collaborators": list(whiteboard.collaborators),
            "created_by": whiteboard.created_by,
            "created_at": whiteboard.created_at.isoformat(),
            "updated_at": whiteboard.updated_at.isoformat(),
            "version": whiteboard.version
        }
    
    def list_whiteboards(self) -> List[Dict[str, Any]]:
        """List all whiteboards"""
        
        return [
            self.get_whiteboard_info(whiteboard_id)
            for whiteboard_id in self.whiteboards.keys()
        ]
    
    def export_whiteboard(self, whiteboard_id: str) -> Optional[Dict[str, Any]]:
        """Export whiteboard data"""
        
        if whiteboard_id not in self.whiteboards:
            return None
        
        whiteboard = self.whiteboards[whiteboard_id]
        
        return {
            "whiteboard": asdict(whiteboard),
            "export_timestamp": datetime.now().isoformat(),
            "version": "1.0"
        }
    
    def import_whiteboard(self, whiteboard_data: Dict[str, Any]) -> Optional[str]:
        """Import whiteboard data"""
        
        try:
            whiteboard_dict = whiteboard_data["whiteboard"]
            
            # Convert datetime strings back to datetime objects
            whiteboard_dict["created_at"] = datetime.fromisoformat(whiteboard_dict["created_at"])
            whiteboard_dict["updated_at"] = datetime.fromisoformat(whiteboard_dict["updated_at"])
            
            # Convert elements
            elements = {}
            for element_id, element_data in whiteboard_dict["elements"].items():
                element_data["created_at"] = datetime.fromisoformat(element_data["created_at"])
                element_data["updated_at"] = datetime.fromisoformat(element_data["updated_at"])
                element_data["position"] = Point(**element_data["position"])
                
                if element_data.get("start_point"):
                    element_data["start_point"] = Point(**element_data["start_point"])
                if element_data.get("end_point"):
                    element_data["end_point"] = Point(**element_data["end_point"])
                
                elements[element_id] = WhiteboardElement(**element_data)
            
            whiteboard_dict["elements"] = elements
            whiteboard_dict["collaborators"] = set(whiteboard_dict["collaborators"])
            
            whiteboard = Whiteboard(**whiteboard_dict)
            self.whiteboards[whiteboard.id] = whiteboard
            
            return whiteboard.id
            
        except Exception as e:
            print(f"Error importing whiteboard: {e}")
            return None

# Global collaborative whiteboard manager instance
whiteboard_manager = CollaborativeWhiteboardManager()
