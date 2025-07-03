"""
Deep Git Integration & Automated Commits Feature
Integrates directly with Git repositories for automated version control operations.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import git
from git import Repo, InvalidGitRepositoryError
import google.generativeai as genai
from pathlib import Path
import subprocess
import difflib

@dataclass
class CommitInfo:
    hash: str
    message: str
    author: str
    date: datetime
    files_changed: List[str]
    insertions: int
    deletions: int

@dataclass
class BranchInfo:
    name: str
    is_current: bool
    last_commit: str
    last_commit_date: datetime
    ahead: int = 0
    behind: int = 0

@dataclass
class ChangeSet:
    file_path: str
    change_type: str  # added, modified, deleted, renamed
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    diff: Optional[str] = None

class GitIntegrationManager:
    """Manages Git operations and automated commit generation"""
    
    def __init__(self, repo_path: str = ".", model_name: str = "gemini-2.5-pro-exp-03-25"):
        self.repo_path = Path(repo_path)
        self.model_name = model_name
        self.repo: Optional[Repo] = None
        self.conventional_commit_types = {
            'feat': 'A new feature',
            'fix': 'A bug fix',
            'docs': 'Documentation only changes',
            'style': 'Changes that do not affect the meaning of the code',
            'refactor': 'A code change that neither fixes a bug nor adds a feature',
            'perf': 'A code change that improves performance',
            'test': 'Adding missing tests or correcting existing tests',
            'chore': 'Changes to the build process or auxiliary tools',
            'ci': 'Changes to CI configuration files and scripts',
            'build': 'Changes that affect the build system or external dependencies'
        }
        
        self._initialize_repo()
    
    def _initialize_repo(self):
        """Initialize the Git repository connection"""
        try:
            self.repo = Repo(self.repo_path)
            if self.repo.bare:
                raise InvalidGitRepositoryError("Repository is bare")
        except InvalidGitRepositoryError:
            # Try to initialize a new repository
            try:
                self.repo = Repo.init(self.repo_path)
            except Exception as e:
                print(f"Failed to initialize Git repository: {e}")
                self.repo = None
    
    def is_git_repo(self) -> bool:
        """Check if the current directory is a Git repository"""
        return self.repo is not None and not self.repo.bare
    
    def get_repo_status(self) -> Dict[str, Any]:
        """Get comprehensive repository status"""
        if not self.is_git_repo():
            return {"error": "Not a Git repository"}
        
        try:
            status = {
                "branch": self.repo.active_branch.name,
                "commit": self.repo.head.commit.hexsha[:8],
                "commit_message": self.repo.head.commit.message.strip(),
                "is_dirty": self.repo.is_dirty(),
                "untracked_files": self.repo.untracked_files,
                "modified_files": [item.a_path for item in self.repo.index.diff(None)],
                "staged_files": [item.a_path for item in self.repo.index.diff("HEAD")],
                "remote_url": self._get_remote_url(),
                "ahead_behind": self._get_ahead_behind_count()
            }
            return status
        except Exception as e:
            return {"error": str(e)}
    
    def _get_remote_url(self) -> Optional[str]:
        """Get the remote URL of the repository"""
        try:
            if 'origin' in self.repo.remotes:
                return self.repo.remotes.origin.url
            elif self.repo.remotes:
                return self.repo.remotes[0].url
        except:
            pass
        return None
    
    def _get_ahead_behind_count(self) -> Dict[str, int]:
        """Get how many commits ahead/behind the current branch is"""
        try:
            if 'origin' in self.repo.remotes:
                remote_branch = f"origin/{self.repo.active_branch.name}"
                if remote_branch in [ref.name for ref in self.repo.refs]:
                    ahead = len(list(self.repo.iter_commits(f"{remote_branch}..HEAD")))
                    behind = len(list(self.repo.iter_commits(f"HEAD..{remote_branch}")))
                    return {"ahead": ahead, "behind": behind}
        except:
            pass
        return {"ahead": 0, "behind": 0}
    
    def get_branches(self) -> List[BranchInfo]:
        """Get information about all branches"""
        if not self.is_git_repo():
            return []
        
        branches = []
        try:
            for branch in self.repo.branches:
                branch_info = BranchInfo(
                    name=branch.name,
                    is_current=branch == self.repo.active_branch,
                    last_commit=branch.commit.hexsha[:8],
                    last_commit_date=datetime.fromtimestamp(branch.commit.committed_date)
                )
                branches.append(branch_info)
        except Exception as e:
            print(f"Error getting branches: {e}")
        
        return branches
    
    def create_branch(self, branch_name: str, from_branch: str = None) -> bool:
        """Create a new branch"""
        if not self.is_git_repo():
            return False
        
        try:
            if from_branch:
                source_branch = self.repo.branches[from_branch]
                new_branch = self.repo.create_head(branch_name, source_branch)
            else:
                new_branch = self.repo.create_head(branch_name)
            
            return True
        except Exception as e:
            print(f"Error creating branch: {e}")
            return False
    
    def switch_branch(self, branch_name: str) -> bool:
        """Switch to a different branch"""
        if not self.is_git_repo():
            return False
        
        try:
            self.repo.git.checkout(branch_name)
            return True
        except Exception as e:
            print(f"Error switching branch: {e}")
            return False
    
    def get_changes(self) -> List[ChangeSet]:
        """Get detailed information about current changes"""
        if not self.is_git_repo():
            return []
        
        changes = []
        
        try:
            # Get modified files
            for item in self.repo.index.diff(None):
                change = ChangeSet(
                    file_path=item.a_path,
                    change_type="modified"
                )
                
                # Get file content
                try:
                    with open(os.path.join(self.repo_path, item.a_path), 'r') as f:
                        change.new_content = f.read()
                    
                    # Get old content from Git
                    try:
                        change.old_content = self.repo.git.show(f"HEAD:{item.a_path}")
                    except:
                        change.old_content = ""
                    
                    # Generate diff
                    change.diff = self._generate_diff(change.old_content, change.new_content, item.a_path)
                    
                except Exception as e:
                    change.diff = f"Error reading file: {e}"
                
                changes.append(change)
            
            # Get untracked files
            for file_path in self.repo.untracked_files:
                change = ChangeSet(
                    file_path=file_path,
                    change_type="added"
                )
                
                try:
                    with open(os.path.join(self.repo_path, file_path), 'r') as f:
                        change.new_content = f.read()
                    change.old_content = ""
                    change.diff = self._generate_diff("", change.new_content, file_path)
                except Exception as e:
                    change.diff = f"Error reading file: {e}"
                
                changes.append(change)
            
        except Exception as e:
            print(f"Error getting changes: {e}")
        
        return changes
    
    def _generate_diff(self, old_content: str, new_content: str, file_path: str) -> str:
        """Generate a unified diff between old and new content"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines, 
            new_lines, 
            fromfile=f"a/{file_path}", 
            tofile=f"b/{file_path}",
            lineterm=""
        )
        
        return ''.join(diff)
    
    async def generate_commit_message(self, changes: List[ChangeSet] = None) -> str:
        """Generate a conventional commit message based on changes"""
        if not changes:
            changes = self.get_changes()
        
        if not changes:
            return "chore: no changes detected"
        
        # Prepare context for AI
        changes_summary = []
        for change in changes:
            summary = {
                "file": change.file_path,
                "type": change.change_type,
                "diff_preview": change.diff[:500] + "..." if change.diff and len(change.diff) > 500 else change.diff
            }
            changes_summary.append(summary)
        
        prompt = f"""
        Generate a conventional commit message for the following changes:
        
        Changes:
        {json.dumps(changes_summary, indent=2)}
        
        Conventional Commit Types:
        {json.dumps(self.conventional_commit_types, indent=2)}
        
        Rules:
        1. Use the format: type(scope): description
        2. Keep the description under 50 characters
        3. Use present tense ("add" not "added")
        4. Don't capitalize the first letter of description
        5. No period at the end
        6. If multiple types of changes, choose the most significant
        7. Scope is optional but helpful (e.g., "auth", "ui", "api")
        
        Examples:
        - feat(auth): add user login functionality
        - fix(ui): resolve button alignment issue
        - docs: update installation instructions
        - refactor: simplify data processing logic
        
        Return only the commit message, nothing else.
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            commit_message = response.text.strip()
            
            # Validate the commit message format
            if self._validate_conventional_commit(commit_message):
                return commit_message
            else:
                # Fallback to a simple message
                return f"chore: update {len(changes)} file{'s' if len(changes) > 1 else ''}"
                
        except Exception as e:
            print(f"Error generating commit message: {e}")
            return f"chore: update {len(changes)} file{'s' if len(changes) > 1 else ''}"
    
    def _validate_conventional_commit(self, message: str) -> bool:
        """Validate if a commit message follows conventional commit format"""
        pattern = r'^(feat|fix|docs|style|refactor|perf|test|chore|ci|build)(\(.+\))?: .{1,50}$'
        return bool(re.match(pattern, message))
    
    def stage_files(self, file_paths: List[str] = None) -> bool:
        """Stage files for commit"""
        if not self.is_git_repo():
            return False
        
        try:
            if file_paths:
                self.repo.index.add(file_paths)
            else:
                # Stage all changes
                self.repo.git.add(A=True)
            return True
        except Exception as e:
            print(f"Error staging files: {e}")
            return False
    
    async def auto_commit(self, message: str = None, stage_all: bool = True) -> bool:
        """Automatically stage and commit changes"""
        if not self.is_git_repo():
            return False
        
        try:
            # Stage files if requested
            if stage_all:
                if not self.stage_files():
                    return False
            
            # Check if there are staged changes
            if not self.repo.index.diff("HEAD"):
                print("No staged changes to commit")
                return False
            
            # Generate commit message if not provided
            if not message:
                changes = self.get_changes()
                message = await self.generate_commit_message(changes)
            
            # Create the commit
            self.repo.index.commit(message)
            print(f"Committed with message: {message}")
            return True
            
        except Exception as e:
            print(f"Error creating commit: {e}")
            return False
    
    def get_commit_history(self, max_count: int = 10) -> List[CommitInfo]:
        """Get recent commit history"""
        if not self.is_git_repo():
            return []
        
        commits = []
        try:
            for commit in self.repo.iter_commits(max_count=max_count):
                # Get file statistics
                stats = commit.stats.total
                
                commit_info = CommitInfo(
                    hash=commit.hexsha[:8],
                    message=commit.message.strip(),
                    author=str(commit.author),
                    date=datetime.fromtimestamp(commit.committed_date),
                    files_changed=list(commit.stats.files.keys()),
                    insertions=stats['insertions'],
                    deletions=stats['deletions']
                )
                commits.append(commit_info)
        except Exception as e:
            print(f"Error getting commit history: {e}")
        
        return commits
    
    def create_feature_branch(self, feature_name: str) -> Tuple[bool, str]:
        """Create a feature branch with conventional naming"""
        # Sanitize feature name
        branch_name = f"feature/{re.sub(r'[^a-zA-Z0-9-]', '-', feature_name.lower())}"
        
        if self.create_branch(branch_name):
            if self.switch_branch(branch_name):
                return True, branch_name
            else:
                return False, f"Created branch {branch_name} but failed to switch to it"
        else:
            return False, f"Failed to create branch {branch_name}"
    
    def create_hotfix_branch(self, fix_name: str) -> Tuple[bool, str]:
        """Create a hotfix branch with conventional naming"""
        branch_name = f"hotfix/{re.sub(r'[^a-zA-Z0-9-]', '-', fix_name.lower())}"
        
        if self.create_branch(branch_name):
            if self.switch_branch(branch_name):
                return True, branch_name
            else:
                return False, f"Created branch {branch_name} but failed to switch to it"
        else:
            return False, f"Failed to create branch {branch_name}"
    
    def push_changes(self, branch_name: str = None, create_remote: bool = True) -> bool:
        """Push changes to remote repository"""
        if not self.is_git_repo():
            return False
        
        try:
            if not branch_name:
                branch_name = self.repo.active_branch.name
            
            # Check if remote exists
            if 'origin' not in self.repo.remotes:
                print("No remote 'origin' configured")
                return False
            
            origin = self.repo.remotes.origin
            
            if create_remote:
                # Push and set upstream
                origin.push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)
            else:
                origin.push()
            
            return True
            
        except Exception as e:
            print(f"Error pushing changes: {e}")
            return False
    
    def get_file_history(self, file_path: str, max_count: int = 10) -> List[CommitInfo]:
        """Get commit history for a specific file"""
        if not self.is_git_repo():
            return []
        
        commits = []
        try:
            for commit in self.repo.iter_commits(paths=file_path, max_count=max_count):
                commit_info = CommitInfo(
                    hash=commit.hexsha[:8],
                    message=commit.message.strip(),
                    author=str(commit.author),
                    date=datetime.fromtimestamp(commit.committed_date),
                    files_changed=[file_path],
                    insertions=0,  # Would need more complex calculation
                    deletions=0
                )
                commits.append(commit_info)
        except Exception as e:
            print(f"Error getting file history: {e}")
        
        return commits
    
    def revert_file(self, file_path: str) -> bool:
        """Revert a file to its last committed state"""
        if not self.is_git_repo():
            return False
        
        try:
            self.repo.git.checkout('HEAD', file_path)
            return True
        except Exception as e:
            print(f"Error reverting file: {e}")
            return False
    
    def get_blame(self, file_path: str) -> Dict[int, Dict[str, Any]]:
        """Get blame information for a file"""
        if not self.is_git_repo():
            return {}
        
        blame_info = {}
        try:
            blame = self.repo.blame('HEAD', file_path)
            for line_num, (commit, line) in enumerate(blame, 1):
                blame_info[line_num] = {
                    'commit': commit.hexsha[:8],
                    'author': str(commit.author),
                    'date': datetime.fromtimestamp(commit.committed_date),
                    'line': line
                }
        except Exception as e:
            print(f"Error getting blame: {e}")
        
        return blame_info

# Global Git integration manager instance
git_manager = GitIntegrationManager()
