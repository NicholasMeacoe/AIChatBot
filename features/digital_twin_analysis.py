"""
Digital Twin of the Codebase Feature - Part 2
Analysis, querying, and architectural insights for the digital twin.
"""

import json
import networkx as nx
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime
import google.generativeai as genai
from .digital_twin import DigitalTwin, CodeEntity, CodeRelationship, ArchitecturalPattern, CodebaseSnapshot

class DigitalTwinAnalyzer:
    """Provides analysis and querying capabilities for the digital twin"""
    
    def __init__(self, digital_twin: DigitalTwin):
        self.twin = digital_twin
    
    def _build_knowledge_graph(self):
        """Build the knowledge graph from entities and relationships"""
        
        self.twin.knowledge_graph.clear()
        
        # Add entities as nodes
        for entity_id, entity in self.twin.entities.items():
            self.twin.knowledge_graph.add_node(entity_id, **asdict(entity))
        
        # Add relationships as edges
        for relationship in self.twin.relationships:
            self.twin.knowledge_graph.add_edge(
                relationship.source_id,
                relationship.target_id,
                relationship_type=relationship.relationship_type,
                strength=relationship.strength,
                **relationship.metadata
            )
    
    async def _detect_architectural_patterns(self):
        """Detect architectural patterns in the codebase"""
        
        patterns = []
        
        # Detect MVC pattern
        mvc_pattern = self._detect_mvc_pattern()
        if mvc_pattern:
            patterns.append(mvc_pattern)
        
        # Detect Singleton pattern
        singleton_patterns = self._detect_singleton_pattern()
        patterns.extend(singleton_patterns)
        
        # Detect Factory pattern
        factory_patterns = self._detect_factory_pattern()
        patterns.extend(factory_patterns)
        
        # Detect Observer pattern
        observer_patterns = self._detect_observer_pattern()
        patterns.extend(observer_patterns)
        
        # Use AI to detect more complex patterns
        ai_patterns = await self._ai_detect_patterns()
        patterns.extend(ai_patterns)
        
        self.twin.architectural_patterns = patterns
    
    def _detect_mvc_pattern(self) -> Optional[ArchitecturalPattern]:
        """Detect Model-View-Controller pattern"""
        
        models = []
        views = []
        controllers = []
        
        for entity_id, entity in self.twin.entities.items():
            name_lower = entity.name.lower()
            file_path_lower = entity.file_path.lower()
            
            if 'model' in name_lower or 'model' in file_path_lower:
                models.append(entity_id)
            elif 'view' in name_lower or 'view' in file_path_lower:
                views.append(entity_id)
            elif 'controller' in name_lower or 'controller' in file_path_lower:
                controllers.append(entity_id)
        
        if models and views and controllers:
            return ArchitecturalPattern(
                pattern_name="Model-View-Controller (MVC)",
                description="Separation of concerns pattern with models, views, and controllers",
                entities_involved=models + views + controllers,
                confidence=0.8,
                evidence=[
                    f"Found {len(models)} model entities",
                    f"Found {len(views)} view entities",
                    f"Found {len(controllers)} controller entities"
                ]
            )
        
        return None
    
    def _detect_singleton_pattern(self) -> List[ArchitecturalPattern]:
        """Detect Singleton pattern instances"""
        
        patterns = []
        
        for entity_id, entity in self.twin.entities.items():
            if entity.entity_type == "class":
                # Look for singleton indicators in the entity
                singleton_indicators = 0
                evidence = []
                
                # Check for common singleton naming
                if 'singleton' in entity.name.lower():
                    singleton_indicators += 2
                    evidence.append("Class name contains 'singleton'")
                
                # Check for getInstance method (would need more detailed parsing)
                # This is a simplified check
                if singleton_indicators >= 1:
                    patterns.append(ArchitecturalPattern(
                        pattern_name="Singleton",
                        description=f"Singleton pattern implementation in {entity.name}",
                        entities_involved=[entity_id],
                        confidence=0.6,
                        evidence=evidence
                    ))
        
        return patterns
    
    def _detect_factory_pattern(self) -> List[ArchitecturalPattern]:
        """Detect Factory pattern instances"""
        
        patterns = []
        
        for entity_id, entity in self.twin.entities.items():
            if entity.entity_type in ["class", "function"]:
                name_lower = entity.name.lower()
                
                if 'factory' in name_lower or 'create' in name_lower:
                    patterns.append(ArchitecturalPattern(
                        pattern_name="Factory",
                        description=f"Factory pattern implementation in {entity.name}",
                        entities_involved=[entity_id],
                        confidence=0.7,
                        evidence=[f"Entity name suggests factory pattern: {entity.name}"]
                    ))
        
        return patterns
    
    def _detect_observer_pattern(self) -> List[ArchitecturalPattern]:
        """Detect Observer pattern instances"""
        
        patterns = []
        
        observers = []
        subjects = []
        
        for entity_id, entity in self.twin.entities.items():
            name_lower = entity.name.lower()
            
            if 'observer' in name_lower or 'listener' in name_lower:
                observers.append(entity_id)
            elif 'subject' in name_lower or 'observable' in name_lower:
                subjects.append(entity_id)
        
        if observers and subjects:
            patterns.append(ArchitecturalPattern(
                pattern_name="Observer",
                description="Observer pattern with subjects and observers",
                entities_involved=observers + subjects,
                confidence=0.8,
                evidence=[
                    f"Found {len(observers)} observer entities",
                    f"Found {len(subjects)} subject entities"
                ]
            ))
        
        return patterns
    
    async def _ai_detect_patterns(self) -> List[ArchitecturalPattern]:
        """Use AI to detect complex architectural patterns"""
        
        # Prepare codebase summary for AI analysis
        summary = {
            "total_entities": len(self.twin.entities),
            "entity_types": Counter(entity.entity_type for entity in self.twin.entities.values()),
            "file_types": Counter(Path(entity.file_path).suffix for entity in self.twin.entities.values()),
            "common_names": Counter(entity.name for entity in self.twin.entities.values()).most_common(20),
            "relationships": Counter(rel.relationship_type for rel in self.twin.relationships)
        }
        
        pattern_prompt = f"""
        Analyze the following codebase structure and identify architectural patterns:
        
        Codebase Summary:
        {json.dumps(summary, indent=2)}
        
        Sample Entities:
        {json.dumps([
            {
                "name": entity.name,
                "type": entity.entity_type,
                "file": Path(entity.file_path).name,
                "dependencies": len(entity.dependencies)
            }
            for entity in list(self.twin.entities.values())[:10]
        ], indent=2)}
        
        Please identify architectural patterns and return a JSON response:
        {{
            "patterns": [
                {{
                    "pattern_name": "Pattern Name",
                    "description": "Description of the pattern",
                    "confidence": 0.8,
                    "evidence": ["evidence1", "evidence2"],
                    "entities_involved": ["entity_names_or_types"]
                }}
            ]
        }}
        
        Look for patterns like:
        - Layered Architecture
        - Microservices
        - Repository Pattern
        - Strategy Pattern
        - Command Pattern
        - Decorator Pattern
        - Adapter Pattern
        """
        
        try:
            model = genai.GenerativeModel(self.twin.model_name)
            response = model.generate_content(pattern_prompt)
            
            ai_response = json.loads(response.text.strip())
            patterns = []
            
            for pattern_data in ai_response.get("patterns", []):
                pattern = ArchitecturalPattern(
                    pattern_name=pattern_data.get("pattern_name", "Unknown Pattern"),
                    description=pattern_data.get("description", ""),
                    entities_involved=pattern_data.get("entities_involved", []),
                    confidence=pattern_data.get("confidence", 0.5),
                    evidence=pattern_data.get("evidence", [])
                )
                patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            print(f"AI pattern detection failed: {e}")
            return []
    
    def _calculate_complexity_metrics(self):
        """Calculate various complexity metrics for the codebase"""
        
        metrics = {}
        
        # Cyclomatic complexity
        total_complexity = sum(entity.complexity for entity in self.twin.entities.values())
        avg_complexity = total_complexity / len(self.twin.entities) if self.twin.entities else 0
        
        metrics["total_cyclomatic_complexity"] = total_complexity
        metrics["average_cyclomatic_complexity"] = avg_complexity
        
        # Coupling metrics
        coupling_data = self._calculate_coupling_metrics()
        metrics.update(coupling_data)
        
        # Cohesion metrics
        cohesion_data = self._calculate_cohesion_metrics()
        metrics.update(cohesion_data)
        
        # Size metrics
        size_data = self._calculate_size_metrics()
        metrics.update(size_data)
        
        self.twin.complexity_metrics = metrics
    
    def _calculate_coupling_metrics(self) -> Dict[str, float]:
        """Calculate coupling metrics"""
        
        if not self.twin.knowledge_graph.nodes():
            return {}
        
        # Afferent coupling (incoming dependencies)
        afferent_coupling = {}
        efferent_coupling = {}
        
        for node in self.twin.knowledge_graph.nodes():
            afferent_coupling[node] = self.twin.knowledge_graph.in_degree(node)
            efferent_coupling[node] = self.twin.knowledge_graph.out_degree(node)
        
        avg_afferent = sum(afferent_coupling.values()) / len(afferent_coupling)
        avg_efferent = sum(efferent_coupling.values()) / len(efferent_coupling)
        
        return {
            "average_afferent_coupling": avg_afferent,
            "average_efferent_coupling": avg_efferent,
            "max_afferent_coupling": max(afferent_coupling.values()) if afferent_coupling else 0,
            "max_efferent_coupling": max(efferent_coupling.values()) if efferent_coupling else 0
        }
    
    def _calculate_cohesion_metrics(self) -> Dict[str, float]:
        """Calculate cohesion metrics"""
        
        # Simplified cohesion calculation
        # In a real implementation, this would analyze method interactions within classes
        
        class_entities = [e for e in self.twin.entities.values() if e.entity_type == "class"]
        
        if not class_entities:
            return {"average_class_cohesion": 0.0}
        
        # Placeholder calculation - would need more detailed analysis
        cohesion_scores = []
        for entity in class_entities:
            # Simple heuristic: classes with more methods might have lower cohesion
            method_count = len([e for e in self.twin.entities.values() 
                              if e.file_path == entity.file_path and e.entity_type == "function"])
            cohesion_score = 1.0 / (1.0 + method_count * 0.1)  # Simplified
            cohesion_scores.append(cohesion_score)
        
        avg_cohesion = sum(cohesion_scores) / len(cohesion_scores)
        
        return {"average_class_cohesion": avg_cohesion}
    
    def _calculate_size_metrics(self) -> Dict[str, float]:
        """Calculate size-related metrics"""
        
        total_entities = len(self.twin.entities)
        total_files = len(set(entity.file_path for entity in self.twin.entities.values()))
        
        # Lines of code (simplified - would need actual line counting)
        total_lines = sum(entity.line_end - entity.line_start + 1 for entity in self.twin.entities.values())
        
        return {
            "total_entities": total_entities,
            "total_files": total_files,
            "estimated_lines_of_code": total_lines,
            "entities_per_file": total_entities / total_files if total_files > 0 else 0
        }
    
    def _calculate_health_metrics(self):
        """Calculate overall codebase health metrics"""
        
        metrics = {}
        
        # Complexity health (lower complexity is better)
        avg_complexity = self.twin.complexity_metrics.get("average_cyclomatic_complexity", 0)
        complexity_health = max(0, 1.0 - (avg_complexity - 1) / 10)  # Normalize to 0-1
        
        # Coupling health (lower coupling is better)
        avg_coupling = self.twin.complexity_metrics.get("average_efferent_coupling", 0)
        coupling_health = max(0, 1.0 - avg_coupling / 10)  # Normalize to 0-1
        
        # Pattern health (more patterns might indicate better architecture)
        pattern_count = len(self.twin.architectural_patterns)
        pattern_health = min(1.0, pattern_count / 5)  # Normalize to 0-1
        
        # Overall health score
        overall_health = (complexity_health + coupling_health + pattern_health) / 3
        
        metrics.update({
            "complexity_health": complexity_health,
            "coupling_health": coupling_health,
            "pattern_health": pattern_health,
            "overall_health": overall_health
        })
        
        self.twin.health_metrics = metrics
    
    def _create_snapshot(self) -> CodebaseSnapshot:
        """Create a snapshot of the current codebase state"""
        
        return CodebaseSnapshot(
            timestamp=datetime.now(),
            total_files=len(set(entity.file_path for entity in self.twin.entities.values())),
            total_lines=self.twin.complexity_metrics.get("estimated_lines_of_code", 0),
            total_entities=len(self.twin.entities),
            total_relationships=len(self.twin.relationships),
            complexity_metrics=self.twin.complexity_metrics.copy(),
            architectural_patterns=self.twin.architectural_patterns.copy(),
            health_score=self.twin.health_metrics.get("overall_health", 0.0)
        )
    
    async def query_codebase(self, query: str) -> Dict[str, Any]:
        """Answer questions about the codebase using the digital twin"""
        
        query_prompt = f"""
        Answer the following question about the codebase using the provided information:
        
        Question: {query}
        
        Codebase Information:
        - Total entities: {len(self.twin.entities)}
        - Entity types: {dict(Counter(entity.entity_type for entity in self.twin.entities.values()))}
        - Architectural patterns: {[p.pattern_name for p in self.twin.architectural_patterns]}
        - Health score: {self.twin.health_metrics.get('overall_health', 0.0):.2f}
        - Complexity metrics: {json.dumps(self.twin.complexity_metrics, indent=2)}
        
        Sample entities:
        {json.dumps([
            {
                "name": entity.name,
                "type": entity.entity_type,
                "file": entity.file_path,
                "complexity": entity.complexity,
                "dependencies": len(entity.dependencies)
            }
            for entity in list(self.twin.entities.values())[:10]
        ], indent=2)}
        
        Please provide a comprehensive answer based on the codebase analysis.
        """
        
        try:
            model = genai.GenerativeModel(self.twin.model_name)
            response = model.generate_content(query_prompt)
            
            return {
                "query": query,
                "answer": response.text.strip(),
                "timestamp": datetime.now().isoformat(),
                "confidence": 0.8
            }
            
        except Exception as e:
            return {
                "query": query,
                "answer": f"Unable to process query: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "confidence": 0.0
            }
    
    def find_similar_entities(self, entity_id: str, similarity_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Find entities similar to the given entity"""
        
        if entity_id not in self.twin.entities:
            return []
        
        target_entity = self.twin.entities[entity_id]
        similar_entities = []
        
        for other_id, other_entity in self.twin.entities.items():
            if other_id == entity_id:
                continue
            
            similarity = self._calculate_entity_similarity(target_entity, other_entity)
            
            if similarity >= similarity_threshold:
                similar_entities.append({
                    "entity_id": other_id,
                    "entity_name": other_entity.name,
                    "entity_type": other_entity.entity_type,
                    "similarity": similarity,
                    "file_path": other_entity.file_path
                })
        
        # Sort by similarity
        similar_entities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similar_entities
    
    def _calculate_entity_similarity(self, entity1: CodeEntity, entity2: CodeEntity) -> float:
        """Calculate similarity between two entities"""
        
        similarity = 0.0
        
        # Type similarity
        if entity1.entity_type == entity2.entity_type:
            similarity += 0.3
        
        # Name similarity (simple string similarity)
        name_similarity = self._string_similarity(entity1.name, entity2.name)
        similarity += name_similarity * 0.3
        
        # Complexity similarity
        if entity1.complexity > 0 and entity2.complexity > 0:
            complexity_ratio = min(entity1.complexity, entity2.complexity) / max(entity1.complexity, entity2.complexity)
            similarity += complexity_ratio * 0.2
        
        # Dependency similarity
        common_deps = len(entity1.dependencies.intersection(entity2.dependencies))
        total_deps = len(entity1.dependencies.union(entity2.dependencies))
        if total_deps > 0:
            dep_similarity = common_deps / total_deps
            similarity += dep_similarity * 0.2
        
        return min(similarity, 1.0)
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using simple character overlap"""
        
        if not str1 or not str2:
            return 0.0
        
        str1_lower = str1.lower()
        str2_lower = str2.lower()
        
        if str1_lower == str2_lower:
            return 1.0
        
        # Simple character overlap
        common_chars = len(set(str1_lower).intersection(set(str2_lower)))
        total_chars = len(set(str1_lower).union(set(str2_lower)))
        
        return common_chars / total_chars if total_chars > 0 else 0.0
    
    def get_impact_analysis(self, entity_id: str) -> Dict[str, Any]:
        """Analyze the impact of changing a specific entity"""
        
        if entity_id not in self.twin.entities:
            return {"error": "Entity not found"}
        
        entity = self.twin.entities[entity_id]
        
        # Find direct dependents
        direct_dependents = []
        for other_id, other_entity in self.twin.entities.items():
            if entity_id in other_entity.dependencies:
                direct_dependents.append(other_id)
        
        # Find indirect dependents using graph traversal
        indirect_dependents = set()
        if self.twin.knowledge_graph.has_node(entity_id):
            # Get all nodes reachable from this entity
            reachable = nx.descendants(self.twin.knowledge_graph, entity_id)
            indirect_dependents = reachable - set(direct_dependents)
        
        # Calculate impact score
        impact_score = len(direct_dependents) * 1.0 + len(indirect_dependents) * 0.5
        
        return {
            "entity_id": entity_id,
            "entity_name": entity.name,
            "direct_dependents": len(direct_dependents),
            "indirect_dependents": len(indirect_dependents),
            "total_impact": len(direct_dependents) + len(indirect_dependents),
            "impact_score": impact_score,
            "risk_level": "high" if impact_score > 10 else "medium" if impact_score > 5 else "low",
            "affected_files": list(set(
                self.twin.entities[dep_id].file_path 
                for dep_id in direct_dependents + list(indirect_dependents)
                if dep_id in self.twin.entities
            ))
        }

# Extend the DigitalTwin class with analysis capabilities
def extend_digital_twin():
    """Extend the DigitalTwin class with analysis methods"""
    
    def build_knowledge_graph(self):
        analyzer = DigitalTwinAnalyzer(self)
        analyzer._build_knowledge_graph()
    
    async def detect_architectural_patterns(self):
        analyzer = DigitalTwinAnalyzer(self)
        await analyzer._detect_architectural_patterns()
    
    def calculate_complexity_metrics(self):
        analyzer = DigitalTwinAnalyzer(self)
        analyzer._calculate_complexity_metrics()
    
    def calculate_health_metrics(self):
        analyzer = DigitalTwinAnalyzer(self)
        analyzer._calculate_health_metrics()
    
    def create_snapshot(self):
        analyzer = DigitalTwinAnalyzer(self)
        return analyzer._create_snapshot()
    
    async def query_codebase(self, query: str):
        analyzer = DigitalTwinAnalyzer(self)
        return await analyzer.query_codebase(query)
    
    def find_similar_entities(self, entity_id: str, similarity_threshold: float = 0.5):
        analyzer = DigitalTwinAnalyzer(self)
        return analyzer.find_similar_entities(entity_id, similarity_threshold)
    
    def get_impact_analysis(self, entity_id: str):
        analyzer = DigitalTwinAnalyzer(self)
        return analyzer.get_impact_analysis(entity_id)
    
    # Add methods to DigitalTwin class
    DigitalTwin._build_knowledge_graph = build_knowledge_graph
    DigitalTwin._detect_architectural_patterns = detect_architectural_patterns
    DigitalTwin._calculate_complexity_metrics = calculate_complexity_metrics
    DigitalTwin._calculate_health_metrics = calculate_health_metrics
    DigitalTwin._create_snapshot = create_snapshot
    DigitalTwin.query_codebase = query_codebase
    DigitalTwin.find_similar_entities = find_similar_entities
    DigitalTwin.get_impact_analysis = get_impact_analysis

# Apply the extension
extend_digital_twin()

# Global digital twin instance
digital_twin = DigitalTwin()
