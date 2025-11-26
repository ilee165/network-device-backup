"""
Git repository management for configuration versioning
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
import git
from git import Repo, InvalidGitRepositoryError

logger = logging.getLogger(__name__)


class GitManager:
    """Manages Git repository for configuration storage"""
    
    def __init__(self, repo_path: str):
        """
        Initialize Git manager
        
        Args:
            repo_path: Path to Git repository
        """
        self.repo_path = Path(repo_path)
        self.repo: Optional[Repo] = None
        
    def initialize_repo(self) -> bool:
        """
        Initialize or open Git repository
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            self.repo_path.mkdir(parents=True, exist_ok=True)
            
            # Try to open existing repo
            try:
                self.repo = Repo(self.repo_path)
                logger.info(f"Opened existing Git repository at {self.repo_path}")
            except InvalidGitRepositoryError:
                # Initialize new repo
                self.repo = Repo.init(self.repo_path)
                logger.info(f"Initialized new Git repository at {self.repo_path}")
                
                # Create initial commit
                readme_path = self.repo_path / "README.md"
                with open(readme_path, 'w') as f:
                    f.write("# Network Device Configuration Backups\n\n")
                    f.write("This repository contains automated backups of network device configurations.\n")
                    f.write(f"Created: {datetime.now().isoformat()}\n")
                
                self.repo.index.add(['README.md'])
                self.repo.index.commit("Initial commit")
                logger.info("Created initial commit")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Git repository: {str(e)}")
            return False
    
    def save_config(self, device_name: str, config: str, timestamp: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
        """
        Save device configuration to repository
        
        Args:
            device_name: Name of device
            config: Configuration content
            timestamp: Optional timestamp (uses current time if not provided)
            
        Returns:
            Tuple of (success: bool, file_path: str or None)
        """
        if not self.repo:
            logger.error("Git repository not initialized")
            return False, None
        
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # Create device directory structure: backups/{device_name}/
            device_dir = self.repo_path / "backups" / device_name
            device_dir.mkdir(parents=True, exist_ok=True)
            
            # Save config with timestamp in filename
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
            config_filename = f"config_{timestamp_str}.txt"
            config_path = device_dir / config_filename
            
            # Also maintain a "latest" symlink or copy
            latest_path = device_dir / "latest.txt"
            
            # Write configuration
            with open(config_path, 'w') as f:
                f.write(config)
            
            # Update latest
            with open(latest_path, 'w') as f:
                f.write(config)
            
            logger.info(f"Saved configuration for {device_name} to {config_path}")
            
            # Return relative path from repo root
            rel_path = config_path.relative_to(self.repo_path)
            return True, str(rel_path)
            
        except Exception as e:
            logger.error(f"Failed to save config for {device_name}: {str(e)}")
            return False, None
    
    def commit_changes(self, device_name: str, message: Optional[str] = None) -> bool:
        """
        Commit changes for a device to Git
        
        Args:
            device_name: Name of device
            message: Optional commit message
            
        Returns:
            True if successful, False otherwise
        """
        if not self.repo:
            logger.error("Git repository not initialized")
            return False
        
        try:
            # Add device directory to staging
            device_dir = Path("backups") / device_name
            self.repo.index.add([str(device_dir)])
            
            # Check if there are changes to commit
            if not self.repo.index.diff("HEAD"):
                logger.info(f"No changes to commit for {device_name}")
                return True
            
            # Create commit message
            if message is None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"Backup: {device_name} - {timestamp}"
            
            # Commit
            self.repo.index.commit(message)
            logger.info(f"Committed changes for {device_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit changes for {device_name}: {str(e)}")
            return False
    
    def get_diff(self, device_name: str, compare_to: str = "HEAD~1") -> Optional[str]:
        """
        Get diff for device configuration
        
        Args:
            device_name: Name of device
            compare_to: Git reference to compare against (default: previous commit)
            
        Returns:
            Diff as string, or None if failed
        """
        if not self.repo:
            logger.error("Git repository not initialized")
            return None
        
        try:
            device_path = f"backups/{device_name}/latest.txt"
            
            # Check if file exists in both commits
            try:
                diff = self.repo.git.diff(compare_to, "HEAD", device_path)
                return diff if diff else None
            except git.exc.GitCommandError:
                # File might not exist in previous commit (first backup)
                logger.info(f"No previous version found for {device_name} (likely first backup)")
                return None
            
        except Exception as e:
            logger.error(f"Failed to get diff for {device_name}: {str(e)}")
            return None
    
    def get_last_backup_time(self, device_name: str) -> Optional[datetime]:
        """
        Get timestamp of last backup for device
        
        Args:
            device_name: Name of device
            
        Returns:
            Datetime of last backup, or None if no backup exists
        """
        if not self.repo:
            return None
        
        try:
            device_path = f"backups/{device_name}/latest.txt"
            
            # Get last commit that modified this file
            commits = list(self.repo.iter_commits(paths=device_path, max_count=1))
            if commits:
                return datetime.fromtimestamp(commits[0].committed_date)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get last backup time for {device_name}: {str(e)}")
            return None
    
    def has_changes(self, device_name: str, new_config: str) -> bool:
        """
        Check if new config differs from last backup
        
        Args:
            device_name: Name of device
            new_config: New configuration to compare
            
        Returns:
            True if config has changed, False if identical
        """
        try:
            latest_path = self.repo_path / "backups" / device_name / "latest.txt"
            
            if not latest_path.exists():
                # No previous backup exists
                return True
            
            with open(latest_path, 'r') as f:
                old_config = f.read()
            
            # Compare configs
            return old_config.strip() != new_config.strip()
            
        except Exception as e:
            logger.warning(f"Error comparing configs for {device_name}: {str(e)}")
            # Assume changed to be safe
            return True
    
    def get_history(self, device_name: str, limit: int = 10) -> List[dict]:
        """
        Get commit history for device
        
        Args:
            device_name: Name of device
            limit: Maximum number of commits to return
            
        Returns:
            List of commit information dictionaries
        """
        if not self.repo:
            return []
        
        try:
            device_path = f"backups/{device_name}/latest.txt"
            commits = list(self.repo.iter_commits(paths=device_path, max_count=limit))
            
            history = []
            for commit in commits:
                history.append({
                    'hash': commit.hexsha[:7],
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'date': datetime.fromtimestamp(commit.committed_date),
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get history for {device_name}: {str(e)}")
            return []