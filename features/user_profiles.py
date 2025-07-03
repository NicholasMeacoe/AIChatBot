"""
Personalized User Profiles & Long-Term Memory Feature
Creates persistent user profiles that learn and remember individual preferences and patterns.
"""

import json
import sqlite3
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
import os
from pathlib import Path
import google.generativeai as genai

@dataclass
class CodingPreference:
    language: str
    style_rules: Dict[str, Any] = field(default_factory=dict)
    preferred_patterns: List[str] = field(default_factory=list)
    avoided_patterns: List[str] = field(default_factory=list)
    naming_conventions: Dict[str, str] = field(default_factory=dict)
    indentation: str = "4_spaces"  # 4_spaces, 2_spaces, tabs
    line_length: int = 80
    comment_style: str = "detailed"  # minimal, standard, detailed

@dataclass
class ProjectPreference:
    project_type: str  # web, mobile, desktop, data_science, etc.
    frameworks: List[str] = field(default_factory=list)
    libraries: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    structure_patterns: List[str] = field(default_factory=list)
    testing_preferences: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CommunicationPreference:
    explanation_level: str = "detailed"  # brief, standard, detailed
    code_comments: bool = True
    step_by_step: bool = True
    examples_preferred: bool = True
    preferred_response_format: str = "markdown"  # plain, markdown, structured
    technical_level: str = "intermediate"  # beginner, intermediate, advanced

@dataclass
class WorkflowPattern:
    pattern_name: str
    frequency: int
    last_used: datetime
    steps: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UserProfile:
    user_id: str
    name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    
    # Preferences
    coding_preferences: Dict[str, CodingPreference] = field(default_factory=dict)
    project_preferences: List[ProjectPreference] = field(default_factory=list)
    communication_preferences: CommunicationPreference = field(default_factory=CommunicationPreference)
    
    # Learning data
    frequent_topics: Counter = field(default_factory=Counter)
    workflow_patterns: List[WorkflowPattern] = field(default_factory=list)
    successful_solutions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Context memory
    recent_projects: List[str] = field(default_factory=list)
    current_context: Dict[str, Any] = field(default_factory=dict)
    long_term_goals: List[str] = field(default_factory=list)
    
    # Statistics
    total_interactions: int = 0
    total_code_generated: int = 0
    favorite_languages: Counter = field(default_factory=Counter)
    session_count: int = 0

class UserProfileManager:
    """Manages user profiles and long-term memory"""
    
    def __init__(self, db_path: str = "user_profiles.db", model_name: str = "gemini-2.5-pro-exp-03-25"):
        self.db_path = db_path
        self.model_name = model_name
        self.current_user: Optional[UserProfile] = None
        self.session_data = defaultdict(list)
        
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the user profiles database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_data TEXT,
                created_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interaction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                timestamp TIMESTAMP,
                interaction_type TEXT,
                content TEXT,
                metadata TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                data_type TEXT,
                data_content TEXT,
                confidence REAL,
                timestamp TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_user_id(self, identifier: str = None) -> str:
        """Create a unique user ID based on system/session info"""
        if identifier:
            return hashlib.sha256(identifier.encode()).hexdigest()[:16]
        
        # Use system info to create a semi-persistent ID
        import platform
        import getpass
        
        system_info = f"{platform.node()}_{getpass.getuser()}_{os.getcwd()}"
        return hashlib.sha256(system_info.encode()).hexdigest()[:16]
    
    def load_or_create_profile(self, user_id: str = None) -> UserProfile:
        """Load existing profile or create a new one"""
        if not user_id:
            user_id = self.create_user_id()
        
        # Try to load existing profile
        profile = self._load_profile_from_db(user_id)
        
        if not profile:
            # Create new profile
            profile = UserProfile(user_id=user_id)
            self._save_profile_to_db(profile)
        
        self.current_user = profile
        self.current_user.last_active = datetime.now()
        self.current_user.session_count += 1
        
        return profile
    
    def _load_profile_from_db(self, user_id: str) -> Optional[UserProfile]:
        """Load a user profile from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT profile_data FROM user_profiles WHERE user_id = ?",
            (user_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            try:
                profile_data = json.loads(result[0])
                
                # Convert datetime strings back to datetime objects
                if 'created_at' in profile_data:
                    profile_data['created_at'] = datetime.fromisoformat(profile_data['created_at'])
                if 'last_active' in profile_data:
                    profile_data['last_active'] = datetime.fromisoformat(profile_data['last_active'])
                
                # Convert Counter objects
                if 'frequent_topics' in profile_data:
                    profile_data['frequent_topics'] = Counter(profile_data['frequent_topics'])
                if 'favorite_languages' in profile_data:
                    profile_data['favorite_languages'] = Counter(profile_data['favorite_languages'])
                
                # Convert workflow patterns
                if 'workflow_patterns' in profile_data:
                    patterns = []
                    for pattern_data in profile_data['workflow_patterns']:
                        if 'last_used' in pattern_data:
                            pattern_data['last_used'] = datetime.fromisoformat(pattern_data['last_used'])
                        patterns.append(WorkflowPattern(**pattern_data))
                    profile_data['workflow_patterns'] = patterns
                
                # Convert coding preferences
                if 'coding_preferences' in profile_data:
                    prefs = {}
                    for lang, pref_data in profile_data['coding_preferences'].items():
                        prefs[lang] = CodingPreference(**pref_data)
                    profile_data['coding_preferences'] = prefs
                
                # Convert project preferences
                if 'project_preferences' in profile_data:
                    prefs = []
                    for pref_data in profile_data['project_preferences']:
                        prefs.append(ProjectPreference(**pref_data))
                    profile_data['project_preferences'] = prefs
                
                # Convert communication preferences
                if 'communication_preferences' in profile_data:
                    profile_data['communication_preferences'] = CommunicationPreference(
                        **profile_data['communication_preferences']
                    )
                
                return UserProfile(**profile_data)
                
            except Exception as e:
                print(f"Error loading profile: {e}")
                return None
        
        return None
    
    def _save_profile_to_db(self, profile: UserProfile):
        """Save a user profile to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert profile to JSON-serializable format
        profile_dict = asdict(profile)
        
        # Convert datetime objects to ISO strings
        profile_dict['created_at'] = profile.created_at.isoformat()
        profile_dict['last_active'] = profile.last_active.isoformat()
        
        # Convert Counter objects to regular dicts
        profile_dict['frequent_topics'] = dict(profile.frequent_topics)
        profile_dict['favorite_languages'] = dict(profile.favorite_languages)
        
        # Convert workflow patterns
        patterns = []
        for pattern in profile.workflow_patterns:
            pattern_dict = asdict(pattern)
            pattern_dict['last_used'] = pattern.last_used.isoformat()
            patterns.append(pattern_dict)
        profile_dict['workflow_patterns'] = patterns
        
        profile_json = json.dumps(profile_dict, default=str)
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles 
            (user_id, profile_data, created_at, last_active)
            VALUES (?, ?, ?, ?)
        ''', (
            profile.user_id,
            profile_json,
            profile.created_at,
            profile.last_active
        ))
        
        conn.commit()
        conn.close()
    
    def record_interaction(self, interaction_type: str, content: str, metadata: Dict[str, Any] = None):
        """Record a user interaction for learning purposes"""
        if not self.current_user:
            return
        
        # Store in session data
        self.session_data[interaction_type].append({
            'content': content,
            'metadata': metadata or {},
            'timestamp': datetime.now()
        })
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO interaction_history 
            (user_id, timestamp, interaction_type, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            self.current_user.user_id,
            datetime.now(),
            interaction_type,
            content,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
        
        # Update profile statistics
        self.current_user.total_interactions += 1
        
        # Learn from the interaction
        self._learn_from_interaction(interaction_type, content, metadata)
    
    def _learn_from_interaction(self, interaction_type: str, content: str, metadata: Dict[str, Any] = None):
        """Learn patterns and preferences from user interactions"""
        if not self.current_user:
            return
        
        metadata = metadata or {}
        
        # Learn coding preferences
        if interaction_type == "code_generation":
            language = metadata.get('language', 'unknown')
            if language != 'unknown':
                self.current_user.favorite_languages[language] += 1
                self._analyze_code_style(content, language)
        
        # Learn topic preferences
        if interaction_type in ["question", "request"]:
            topics = self._extract_topics(content)
            for topic in topics:
                self.current_user.frequent_topics[topic] += 1
        
        # Learn workflow patterns
        if interaction_type == "workflow_step":
            self._update_workflow_patterns(content, metadata)
        
        # Update communication preferences based on feedback
        if interaction_type == "feedback":
            self._adjust_communication_preferences(content, metadata)
    
    def _analyze_code_style(self, code: str, language: str):
        """Analyze code to learn user's style preferences"""
        if language not in self.current_user.coding_preferences:
            self.current_user.coding_preferences[language] = CodingPreference(language=language)
        
        pref = self.current_user.coding_preferences[language]
        
        # Analyze indentation
        lines = code.split('\n')
        indented_lines = [line for line in lines if line.startswith((' ', '\t'))]
        
        if indented_lines:
            if any(line.startswith('\t') for line in indented_lines):
                pref.indentation = "tabs"
            elif any(line.startswith('  ') for line in indented_lines):
                if any(line.startswith('    ') for line in indented_lines):
                    pref.indentation = "4_spaces"
                else:
                    pref.indentation = "2_spaces"
        
        # Analyze line length preference
        line_lengths = [len(line) for line in lines if line.strip()]
        if line_lengths:
            avg_length = sum(line_lengths) / len(line_lengths)
            max_length = max(line_lengths)
            
            if max_length > 100:
                pref.line_length = 120
            elif max_length > 80:
                pref.line_length = 100
            else:
                pref.line_length = 80
        
        # Analyze naming conventions
        if language == "python":
            # Check for snake_case vs camelCase
            snake_case_matches = len(re.findall(r'\b[a-z]+_[a-z_]+\b', code))
            camel_case_matches = len(re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b', code))
            
            if snake_case_matches > camel_case_matches:
                pref.naming_conventions['variables'] = 'snake_case'
            else:
                pref.naming_conventions['variables'] = 'camelCase'
        
        # Analyze comment density
        comment_lines = len([line for line in lines if line.strip().startswith('#')])
        total_lines = len([line for line in lines if line.strip()])
        
        if total_lines > 0:
            comment_ratio = comment_lines / total_lines
            if comment_ratio > 0.3:
                pref.comment_style = "detailed"
            elif comment_ratio > 0.1:
                pref.comment_style = "standard"
            else:
                pref.comment_style = "minimal"
    
    def _extract_topics(self, content: str) -> List[str]:
        """Extract topics from user content using keyword analysis"""
        # Common programming and tech topics
        topic_keywords = {
            'web_development': ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'web', 'frontend', 'backend'],
            'data_science': ['pandas', 'numpy', 'matplotlib', 'data', 'analysis', 'machine learning', 'ai'],
            'mobile_development': ['android', 'ios', 'mobile', 'app', 'flutter', 'react native'],
            'database': ['sql', 'database', 'mysql', 'postgresql', 'mongodb', 'query'],
            'api_development': ['api', 'rest', 'graphql', 'endpoint', 'service'],
            'testing': ['test', 'testing', 'unit test', 'integration', 'pytest', 'jest'],
            'deployment': ['deploy', 'docker', 'kubernetes', 'aws', 'cloud', 'ci/cd'],
            'security': ['security', 'authentication', 'authorization', 'encryption', 'ssl'],
            'performance': ['performance', 'optimization', 'speed', 'memory', 'cache']
        }
        
        content_lower = content.lower()
        detected_topics = []
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_topics.append(topic)
        
        return detected_topics
    
    def _update_workflow_patterns(self, step: str, metadata: Dict[str, Any]):
        """Update workflow patterns based on user actions"""
        workflow_name = metadata.get('workflow', 'general')
        
        # Find existing pattern or create new one
        pattern = None
        for p in self.current_user.workflow_patterns:
            if p.pattern_name == workflow_name:
                pattern = p
                break
        
        if not pattern:
            pattern = WorkflowPattern(
                pattern_name=workflow_name,
                frequency=0,
                last_used=datetime.now()
            )
            self.current_user.workflow_patterns.append(pattern)
        
        pattern.steps.append(step)
        pattern.frequency += 1
        pattern.last_used = datetime.now()
        pattern.context.update(metadata)
    
    def _adjust_communication_preferences(self, feedback: str, metadata: Dict[str, Any]):
        """Adjust communication preferences based on user feedback"""
        feedback_lower = feedback.lower()
        
        if any(word in feedback_lower for word in ['too detailed', 'too long', 'verbose']):
            if self.current_user.communication_preferences.explanation_level == 'detailed':
                self.current_user.communication_preferences.explanation_level = 'standard'
            elif self.current_user.communication_preferences.explanation_level == 'standard':
                self.current_user.communication_preferences.explanation_level = 'brief'
        
        elif any(word in feedback_lower for word in ['more detail', 'explain more', 'elaborate']):
            if self.current_user.communication_preferences.explanation_level == 'brief':
                self.current_user.communication_preferences.explanation_level = 'standard'
            elif self.current_user.communication_preferences.explanation_level == 'standard':
                self.current_user.communication_preferences.explanation_level = 'detailed'
        
        if 'no comments' in feedback_lower or 'without comments' in feedback_lower:
            self.current_user.communication_preferences.code_comments = False
        elif 'add comments' in feedback_lower or 'with comments' in feedback_lower:
            self.current_user.communication_preferences.code_comments = True
    
    async def get_personalized_response_style(self) -> Dict[str, Any]:
        """Get the user's preferred response style for AI interactions"""
        if not self.current_user:
            return {}
        
        prefs = self.current_user.communication_preferences
        
        style_guide = {
            'explanation_level': prefs.explanation_level,
            'include_comments': prefs.code_comments,
            'step_by_step': prefs.step_by_step,
            'include_examples': prefs.examples_preferred,
            'response_format': prefs.preferred_response_format,
            'technical_level': prefs.technical_level,
            'favorite_languages': dict(self.current_user.favorite_languages.most_common(3)),
            'frequent_topics': dict(self.current_user.frequent_topics.most_common(5))
        }
        
        return style_guide
    
    async def generate_personalized_prompt(self, base_prompt: str) -> str:
        """Generate a personalized prompt based on user preferences"""
        if not self.current_user:
            return base_prompt
        
        style = await self.get_personalized_response_style()
        
        personalization = f"""
        User Preferences:
        - Explanation level: {style['explanation_level']}
        - Include code comments: {style['include_comments']}
        - Technical level: {style['technical_level']}
        - Preferred languages: {', '.join(style['favorite_languages'].keys())}
        - Common topics: {', '.join(style['frequent_topics'].keys())}
        
        Please tailor your response according to these preferences.
        """
        
        return f"{base_prompt}\n\n{personalization}"
    
    def get_user_context(self) -> Dict[str, Any]:
        """Get relevant user context for the current session"""
        if not self.current_user:
            return {}
        
        return {
            'user_id': self.current_user.user_id,
            'session_count': self.current_user.session_count,
            'total_interactions': self.current_user.total_interactions,
            'recent_projects': self.current_user.recent_projects[-5:],  # Last 5 projects
            'current_context': self.current_user.current_context,
            'favorite_languages': dict(self.current_user.favorite_languages.most_common(3)),
            'frequent_topics': dict(self.current_user.frequent_topics.most_common(5)),
            'workflow_patterns': [p.pattern_name for p in self.current_user.workflow_patterns[-3:]]
        }
    
    def update_current_context(self, context_updates: Dict[str, Any]):
        """Update the current session context"""
        if self.current_user:
            self.current_user.current_context.update(context_updates)
    
    def add_successful_solution(self, problem: str, solution: str, metadata: Dict[str, Any] = None):
        """Record a successful solution for future reference"""
        if not self.current_user:
            return
        
        solution_record = {
            'problem': problem,
            'solution': solution,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
            'success_score': 1.0  # Could be adjusted based on user feedback
        }
        
        self.current_user.successful_solutions.append(solution_record)
        
        # Keep only the most recent 100 solutions
        if len(self.current_user.successful_solutions) > 100:
            self.current_user.successful_solutions = self.current_user.successful_solutions[-100:]
    
    def find_similar_solutions(self, problem: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar solutions from the user's history"""
        if not self.current_user or not self.current_user.successful_solutions:
            return []
        
        # Simple keyword-based similarity (could be enhanced with embeddings)
        problem_words = set(problem.lower().split())
        
        scored_solutions = []
        for solution in self.current_user.successful_solutions:
            solution_words = set(solution['problem'].lower().split())
            similarity = len(problem_words.intersection(solution_words)) / len(problem_words.union(solution_words))
            
            if similarity > 0.1:  # Minimum similarity threshold
                scored_solutions.append((similarity, solution))
        
        # Sort by similarity and return top results
        scored_solutions.sort(key=lambda x: x[0], reverse=True)
        return [solution for _, solution in scored_solutions[:limit]]
    
    def save_profile(self):
        """Save the current user profile"""
        if self.current_user:
            self._save_profile_to_db(self.current_user)
    
    def get_profile_summary(self) -> Dict[str, Any]:
        """Get a summary of the user profile"""
        if not self.current_user:
            return {}
        
        return {
            'user_id': self.current_user.user_id,
            'created_at': self.current_user.created_at.isoformat(),
            'last_active': self.current_user.last_active.isoformat(),
            'total_interactions': self.current_user.total_interactions,
            'session_count': self.current_user.session_count,
            'favorite_languages': dict(self.current_user.favorite_languages.most_common(5)),
            'frequent_topics': dict(self.current_user.frequent_topics.most_common(10)),
            'coding_preferences': {lang: asdict(pref) for lang, pref in self.current_user.coding_preferences.items()},
            'communication_preferences': asdict(self.current_user.communication_preferences),
            'workflow_patterns_count': len(self.current_user.workflow_patterns),
            'successful_solutions_count': len(self.current_user.successful_solutions)
        }

# Global user profile manager instance
user_profile_manager = UserProfileManager()
