#!/usr/bin/env python3
"""
Release Notes Generator for Laboratory Inventory Management System

This script analyzes git commit history and generates structured release notes
based on commit messages and descriptions. It categorizes changes into features,
bug fixes, improvements, and other changes.
"""

import subprocess
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Commit:
    """Represents a git commit with relevant information for release notes."""
    hash: str
    short_hash: str
    author: str
    date: str
    subject: str
    body: str
    files_changed: List[str]
    insertions: int
    deletions: int


@dataclass
class ReleaseSection:
    """Represents a section in the release notes."""
    title: str
    commits: List[Commit]
    description: str = ""


class ReleaseNotesGenerator:
    """Generates release notes from git commit history."""
    
    # Keywords to categorize commits
    FEATURE_KEYWORDS = [
        'add', 'implement', 'create', 'new', 'feature', 'introduce', 
        'support', 'enable', 'allow'
    ]
    
    BUGFIX_KEYWORDS = [
        'fix', 'bug', 'issue', 'resolve', 'correct', 'repair', 'patch',
        'hotfix', 'error', 'crash'
    ]
    
    IMPROVEMENT_KEYWORDS = [
        'improve', 'enhance', 'optimize', 'refactor', 'update', 'upgrade',
        'performance', 'speed', 'efficiency', 'better'
    ]
    
    DOCUMENTATION_KEYWORDS = [
        'doc', 'documentation', 'readme', 'comment', 'guide', 'help',
        'manual', 'example'
    ]
    
    def __init__(self, repo_path: str = "."):
        """Initialize the generator with repository path."""
        self.repo_path = Path(repo_path)
        
    def get_commits(self, since: Optional[str] = None, until: Optional[str] = None) -> List[Commit]:
        """
        Get commits from git history.
        
        Args:
            since: Start date/commit (e.g., 'v1.0.0', '2023-01-01')
            until: End date/commit (default: HEAD)
        
        Returns:
            List of Commit objects
        """
        cmd = ['git', 'log', '--pretty=format:%H|%h|%an|%ad|%s|%b', '--date=iso']
        
        if since:
            if until:
                cmd.append(f'{since}..{until}')
            else:
                cmd.append(f'{since}..HEAD')
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=self.repo_path, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            commits = []
            current_commit_lines = []
            
            for line in result.stdout.split('\n'):
                if '|' in line and len(line.split('|')) >= 5:
                    # Process previous commit if exists
                    if current_commit_lines:
                        commits.append(self._parse_commit_lines(current_commit_lines))
                    
                    # Start new commit
                    current_commit_lines = [line]
                else:
                    # Continuation of commit body
                    if current_commit_lines:
                        current_commit_lines.append(line)
            
            # Process last commit
            if current_commit_lines:
                commits.append(self._parse_commit_lines(current_commit_lines))
                
            return commits
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting commits: {e}")
            return []
    
    def _parse_commit_lines(self, lines: List[str]) -> Commit:
        """Parse commit information from git log output."""
        main_line = lines[0]
        body_lines = lines[1:] if len(lines) > 1 else []
        
        parts = main_line.split('|', 5)
        hash_full = parts[0]
        hash_short = parts[1]
        author = parts[2]
        date = parts[3]
        subject = parts[4]
        body = '\n'.join(body_lines).strip() if body_lines else parts[5] if len(parts) > 5 else ""
        
        # Get file statistics for this commit
        files_changed, insertions, deletions = self._get_commit_stats(hash_full)
        
        return Commit(
            hash=hash_full,
            short_hash=hash_short,
            author=author,
            date=date,
            subject=subject,
            body=body,
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions
        )
    
    def _get_commit_stats(self, commit_hash: str) -> tuple[List[str], int, int]:
        """Get file changes and line statistics for a commit."""
        try:
            # Get files changed
            files_cmd = ['git', 'show', '--name-only', '--pretty=format:', commit_hash]
            files_result = subprocess.run(
                files_cmd, 
                cwd=self.repo_path, 
                capture_output=True, 
                text=True
            )
            files_changed = [f for f in files_result.stdout.strip().split('\n') if f]
            
            # Get insertions/deletions
            stats_cmd = ['git', 'show', '--shortstat', '--pretty=format:', commit_hash]
            stats_result = subprocess.run(
                stats_cmd, 
                cwd=self.repo_path, 
                capture_output=True, 
                text=True
            )
            
            insertions = 0
            deletions = 0
            if stats_result.stdout.strip():
                stats_line = stats_result.stdout.strip()
                # Parse "X files changed, Y insertions(+), Z deletions(-)"
                if 'insertion' in stats_line:
                    ins_match = re.search(r'(\d+) insertion', stats_line)
                    if ins_match:
                        insertions = int(ins_match.group(1))
                
                if 'deletion' in stats_line:
                    del_match = re.search(r'(\d+) deletion', stats_line)
                    if del_match:
                        deletions = int(del_match.group(1))
            
            return files_changed, insertions, deletions
            
        except subprocess.CalledProcessError:
            return [], 0, 0
    
    def categorize_commits(self, commits: List[Commit]) -> Dict[str, List[Commit]]:
        """
        Categorize commits based on keywords in subject and body.
        
        Returns:
            Dictionary with categories as keys and lists of commits as values
        """
        categories = {
            'Features': [],
            'Bug Fixes': [],
            'Improvements': [],
            'Documentation': [],
            'Other Changes': []
        }
        
        for commit in commits:
            text = (commit.subject + ' ' + commit.body).lower()
            
            if any(keyword in text for keyword in self.FEATURE_KEYWORDS):
                categories['Features'].append(commit)
            elif any(keyword in text for keyword in self.BUGFIX_KEYWORDS):
                categories['Bug Fixes'].append(commit)
            elif any(keyword in text for keyword in self.IMPROVEMENT_KEYWORDS):
                categories['Improvements'].append(commit)
            elif any(keyword in text for keyword in self.DOCUMENTATION_KEYWORDS):
                categories['Documentation'].append(commit)
            else:
                categories['Other Changes'].append(commit)
        
        return categories
    
    def generate_markdown_release_notes(
        self, 
        version: str = None, 
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> str:
        """
        Generate release notes in Markdown format.
        
        Args:
            version: Version string for the release
            since: Start commit/tag for changes
            until: End commit/tag for changes
            
        Returns:
            Markdown formatted release notes
        """
        commits = self.get_commits(since, until)
        
        if not commits:
            return "# Release Notes\n\nNo commits found for the specified range."
        
        categories = self.categorize_commits(commits)
        
        # Generate header
        if not version:
            version = f"Release {datetime.now().strftime('%Y.%m.%d')}"
        
        markdown = f"# {version}\n\n"
        markdown += f"**Release Date:** {datetime.now().strftime('%B %d, %Y')}\n\n"
        
        # Add summary statistics
        total_commits = len(commits)
        total_files = len(set(file for commit in commits for file in commit.files_changed))
        total_insertions = sum(commit.insertions for commit in commits)
        total_deletions = sum(commit.deletions for commit in commits)
        
        markdown += "## Summary\n\n"
        markdown += f"- **{total_commits}** commits\n"
        markdown += f"- **{total_files}** files changed\n"
        markdown += f"- **{total_insertions:,}** insertions (+)\n"
        markdown += f"- **{total_deletions:,}** deletions (-)\n\n"
        
        # Add sections for each category
        for category, category_commits in categories.items():
            if not category_commits:
                continue
                
            markdown += f"## {category}\n\n"
            
            for commit in category_commits:
                markdown += f"- **{commit.subject}** ({commit.short_hash})\n"
                
                if commit.body:
                    # Format commit body as bullet points
                    body_lines = [line.strip() for line in commit.body.split('\n') if line.strip()]
                    for line in body_lines[:3]:  # Limit to first 3 lines
                        if line.startswith('-') or line.startswith('*'):
                            markdown += f"  {line}\n"
                        else:
                            markdown += f"  - {line}\n"
                
                markdown += f"  *Author: {commit.author}*\n\n"
        
        # Add detailed changes section
        markdown += "## Detailed Changes\n\n"
        markdown += "### Files Modified\n\n"
        
        all_files = set()
        for commit in commits:
            all_files.update(commit.files_changed)
        
        for file in sorted(all_files):
            markdown += f"- `{file}`\n"
        
        return markdown
    
    def generate_json_release_notes(
        self, 
        version: str = None,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> dict:
        """Generate release notes in JSON format."""
        commits = self.get_commits(since, until)
        categories = self.categorize_commits(commits)
        
        if not version:
            version = f"Release {datetime.now().strftime('%Y.%m.%d')}"
        
        return {
            "version": version,
            "release_date": datetime.now().isoformat(),
            "summary": {
                "total_commits": len(commits),
                "total_files": len(set(file for commit in commits for file in commit.files_changed)),
                "total_insertions": sum(commit.insertions for commit in commits),
                "total_deletions": sum(commit.deletions for commit in commits)
            },
            "categories": {
                category: [asdict(commit) for commit in category_commits]
                for category, category_commits in categories.items()
                if category_commits
            }
        }
    
    def save_release_notes(
        self, 
        output_path: str, 
        format: str = "markdown",
        version: str = None,
        since: Optional[str] = None,
        until: Optional[str] = None
    ):
        """
        Save release notes to file.
        
        Args:
            output_path: Path to save the release notes
            format: 'markdown' or 'json'
            version: Version string
            since: Start commit/tag
            until: End commit/tag
        """
        if format.lower() == "json":
            notes = self.generate_json_release_notes(version, since, until)
            with open(output_path, 'w') as f:
                json.dump(notes, f, indent=2)
        else:
            notes = self.generate_markdown_release_notes(version, since, until)
            with open(output_path, 'w') as f:
                f.write(notes)
        
        print(f"Release notes saved to: {output_path}")


def main():
    """Main function for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate release notes from git commits")
    parser.add_argument("--version", help="Version string for the release")
    parser.add_argument("--since", help="Start commit/tag for changes")
    parser.add_argument("--until", help="End commit/tag for changes")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", 
                        help="Output format")
    parser.add_argument("--repo", default=".", help="Repository path")
    
    args = parser.parse_args()
    
    generator = ReleaseNotesGenerator(args.repo)
    
    if args.output:
        generator.save_release_notes(
            args.output, 
            args.format, 
            args.version, 
            args.since, 
            args.until
        )
    else:
        # Print to stdout
        if args.format == "json":
            notes = generator.generate_json_release_notes(args.version, args.since, args.until)
            print(json.dumps(notes, indent=2))
        else:
            notes = generator.generate_markdown_release_notes(args.version, args.since, args.until)
            print(notes)


if __name__ == "__main__":
    main()