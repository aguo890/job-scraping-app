"""
GitHub integration for committing reports and managing issues
"""
import os
import logging
import subprocess
from typing import Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class GitHubIntegration:
    """Handles GitHub operations"""
    
    def __init__(self, repo: Optional[str] = None, token: Optional[str] = None):
        self.repo = repo or os.getenv('GITHUB_REPOSITORY')
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.api_base = "https://api.github.com"
    
    def commit_and_push_reports(self, files: list, commit_message: Optional[str] = None) -> bool:
        """Commit and push report files to repository"""
        try:
            if not commit_message:
                today = datetime.now().strftime('%Y-%m-%d')
                commit_message = f"Daily job report - {today}"
            
            # Configure git
            subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], check=True)
            subprocess.run(['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'], check=True)
            
            # Add files
            for file in files:
                if os.path.exists(file):
                    subprocess.run(['git', 'add', file], check=True)
                    logger.info(f"Added file: {file}")
            
            # Check if there are changes to commit
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, check=True)
            
            if not result.stdout.strip():
                logger.info("No changes to commit")
                return True
            
            # Commit
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            logger.info(f"Committed changes: {commit_message}")
            
            # Push
            subprocess.run(['git', 'push'], check=True)
            logger.info("Pushed changes to repository")
            
            return True
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error committing and pushing: {e}")
            return False
    
    def find_existing_issue(self, title: str) -> Optional[int]:
        """Find existing issue by title"""
        if not self.token or not self.repo:
            logger.warning("GitHub token or repo not configured")
            return None
        
        try:
            url = f"{self.api_base}/repos/{self.repo}/issues"
            headers = {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            params = {
                'state': 'open',
                'per_page': 100
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            issues = response.json()
            for issue in issues:
                if issue.get('title') == title:
                    return issue.get('number')
            
            return None
        
        except Exception as e:
            logger.error(f"Error finding existing issue: {e}")
            return None
    
    def create_or_update_issue(self, title: str, body: str, labels: Optional[list] = None) -> bool:
        """Create or update a GitHub issue"""
        if not self.token or not self.repo:
            logger.warning("GitHub token or repo not configured - skipping issue creation")
            return False
        
        try:
            headers = {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Check if issue exists
            existing_issue = self.find_existing_issue(title)
            
            if existing_issue:
                # Update existing issue
                url = f"{self.api_base}/repos/{self.repo}/issues/{existing_issue}"
                data = {'body': body}
                if labels:
                    data['labels'] = labels
                
                response = requests.patch(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                
                logger.info(f"Updated issue #{existing_issue}: {title}")
            else:
                # Create new issue
                url = f"{self.api_base}/repos/{self.repo}/issues"
                data = {
                    'title': title,
                    'body': body
                }
                if labels:
                    data['labels'] = labels
                
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                
                issue_number = response.json().get('number')
                logger.info(f"Created issue #{issue_number}: {title}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error creating/updating issue: {e}")
            return False
    
    def create_daily_digest_issue(self, jobs: list, report_path: str) -> bool:
        """Create or update the Daily Roles Digest issue"""
        today = datetime.now().strftime('%Y-%m-%d')
        title = "Daily Roles Digest"
        
        # Create issue body
        body = f"# Daily Job Scraping Digest - {today}\n\n"
        body += "## Summary\n\n"
        body += f"- **Total Jobs**: {len(jobs)}\n"
        body += f"- **Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        body += f"- **Full Report**: [View Report]({report_path})\n\n"
        
        # Top companies
        companies = {}
        for job in jobs:
            company = job.get('company', 'Unknown')
            companies[company] = companies.get(company, 0) + 1
        
        body += "## Top Companies\n\n"
        for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True)[:10]:
            body += f"- **{company}**: {count} jobs\n"
        
        body += "\n## Top 10 Job Opportunities\n\n"
        
        top_jobs = jobs[:10]
        for idx, job in enumerate(top_jobs, 1):
            body += f"### {idx}. {job.get('title', 'N/A')} at {job.get('company', 'N/A')}\n"
            body += f"- **Location**: {job.get('location', 'N/A')}\n"
            body += f"- **Score**: {job.get('score', 0):.1f}\n"
            body += f"- **Apply**: {job.get('url', 'N/A')}\n\n"
        
        body += "---\n\n"
        body += f"*This issue is automatically updated daily. Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        return self.create_or_update_issue(title, body, labels=['job-digest', 'automated'])
