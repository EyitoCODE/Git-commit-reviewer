"""
Git Handler Module
Provides secure, native OS-level interactions with Git repositories.
By bypassing third-party wrappers like GitPython, this module avoids 
Windows-specific recursion limits and excessive memory consumption 
when handling large repository histories.
"""
import os
import tempfile
import subprocess
from typing import List, Dict, Any

def is_remote_url(source: str) -> bool:
    """Determine if the source string represents a remote Git URL."""
    remote_prefixes = ('http://', 'https://', 'git@', 'ssh://', 'git://')
    return source.startswith(remote_prefixes)

def extract_commits_via_cli(repo_path: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Uses native git CLI to extract commits, bypassing GitPython entirely.
    """
    # Security/Robustness: Using \x1e (Record Separator) for fields, 
    # and \x1f (Unit Separator) for commits to prevent multi-line message parsing errors.
    git_format = "%H%x1E%an%x1E%cI%x1E%s%x1F"
    
    try:
        # Execute git log natively to extract the exact formatted string
        result = subprocess.run(
            ["git", "log", "-n", str(limit), f"--pretty=format:{git_format}"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        commits = []
        if not result.stdout.strip():
            return commits
            
        # Split by the \x1f Unit Separator instead of \n
        raw_commits = result.stdout.split('\x1f')
        for raw_commit in raw_commits:
            # Skip empty strings caused by trailing separators
            if not raw_commit.strip():
                continue
                
            # Split exactly 3 times to ensure the message body remains intact
            parts = raw_commit.strip().split('\x1e', 3)
            if len(parts) == 4:
                commits.append({
                    'hash': parts[0],
                    'author': parts[1],
                    'timestamp': parts[2],
                    'message': parts[3].strip()
                })
        return commits
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to read git log natively: {e.stderr}")

def fetch_recent_commits(repo_source: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Given a local path or remote Git URL, return a list of recent commits.
    Uses only native OS subprocesses to completely avoid Python recursion limits.
    """
    commits = []
    
    if is_remote_url(repo_source):
        # Handle remote repository via native subprocess
        # TemporaryDirectory ensures the cloned repo is automatically deleted after extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Performance & Security Optimization:
                # 1. --depth: Performs a shallow clone, saving massive amounts of bandwidth and time.
                # 2. --: Prevents argument injection if the URL is somehow malformed.
                subprocess.run(
                    ["git", "clone", "--depth", str(limit), "--", repo_source, temp_dir],
                    check=True,
                    capture_output=True
                )
                commits = extract_commits_via_cli(temp_dir, limit)
                
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode('utf-8', errors='ignore') if isinstance(e.stderr, bytes) else e.stderr
                raise RuntimeError(f"Native git clone failed. Details: {error_msg}")
    else:
        # Handle local repository
        if not os.path.exists(repo_source):
            raise FileNotFoundError(f"The specified local path does not exist: {repo_source}")
            
        try:
            # Verify the directory is actually a valid git repository before attempting to parse
            subprocess.run(
                ["git", "status"], 
                cwd=repo_source, 
                check=True, 
                capture_output=True
            )
            commits = extract_commits_via_cli(repo_source, limit)
        except subprocess.CalledProcessError:
            raise ValueError(f"The provided directory is not a valid Git repository: {repo_source}")

    return commits