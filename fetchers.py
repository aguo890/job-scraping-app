"""
Job fetchers module for different ATS platforms (Async)
"""
import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional

import json
import os
from utils.network import SafeSession
from utils.smart_filter import job_filter
from utils.schemas import JobListing
from pathlib import Path

logger = logging.getLogger(__name__)
# Base directory for absolute path resolution
BASE_DIR = Path(__file__).resolve().parent

class GreenhouseFetcher:
    """Async Fetcher for Greenhouse API"""
    
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
    
    def __init__(self, client: SafeSession):
        self.client = client
    
    async def fetch_jobs(self, board_token: str, company_name: str, applied_ids: set) -> List[Dict[str, Any]]:
        """Fetch jobs from Greenhouse board asynchronously"""
        url = f"{self.BASE_URL}/{board_token}/jobs?content=true"
        jobs_data = await self.client.fetch_json(url)
        
        if not jobs_data or not isinstance(jobs_data, dict):
            return []
            
        jobs = jobs_data.get('jobs', [])
        
        normalized_jobs = []
        for job in jobs:
            title = job.get('title', '').strip()
            location = job.get('location', {}).get('name', '')
            job_id = f"gh_{board_token}_{job.get('id')}"
            
            # Order of Operations: Applied Check FIRST
            is_applied = job_id in applied_ids
            
            if not is_applied:
                # Gatekeeper: Structural Quality
                job_payload = {
                    'title': title,
                    'location': location,
                    'date_posted': job.get('updated_at', '')
                }
                if not job_filter.passes_hard_filters(job_payload):
                    continue

            job_obj = JobListing.from_dict({
                'id': job_id,
                'title': title,
                'company': company_name,
                'location': location,
                'url': job.get('absolute_url', ''),
                'description': job.get('content', ''),
                'date_posted': job.get('updated_at', ''),
                'source': 'greenhouse',
                'raw_data': job
            })
            
            job_obj.sanitize()
            if job_obj.is_valid():
                normalized_jobs.append(job_obj.to_dict())
        
        logger.info(f"Fetched {len(normalized_jobs)} jobs from Greenhouse for {company_name}")
        return normalized_jobs


class LeverFetcher:
    """Async Fetcher for Lever API"""
    
    def __init__(self, client: SafeSession):
        self.client = client
    
    async def fetch_jobs(self, board_token: str, company_name: str, applied_ids: set) -> List[Dict[str, Any]]:
        """Fetch jobs from Lever API asynchronously"""
        api_url = f"https://api.lever.co/v0/postings/{board_token}"
        jobs = await self.client.fetch_json(api_url)
        
        if not jobs or not isinstance(jobs, list):
            return []
            
        normalized_jobs = []
        for job in jobs:
            title = job.get('text', '').strip()
            job_id = f"lever_{board_token}_{job.get('id')}"
            
            # Robust location parsing
            location = ''
            categories = job.get('categories', {})
            if isinstance(categories, dict) and 'location' in categories:
                loc_data = categories['location']
                if isinstance(loc_data, str):
                    location = loc_data
                elif isinstance(loc_data, list):
                    parts = []
                    for item in loc_data:
                        if isinstance(item, dict):
                            parts.append(item.get('name', ''))
                        elif isinstance(item, str):
                            parts.append(item)
                    location = ', '.join(p for p in parts if p)
            
            # Order of Operations: Applied Check FIRST
            is_applied = job_id in applied_ids
            
            if not is_applied:
                # Gatekeeper: Structural Quality
                job_payload = {
                    'title': title,
                    'location': location,
                    'date_posted': job.get('createdAt', '')
                }
                if not job_filter.passes_hard_filters(job_payload):
                    continue

            job_obj = JobListing.from_dict({
                'id': job_id,
                'title': title,
                'company': company_name,
                'location': location,
                'url': job.get('hostedUrl', ''),
                'description': job.get('description', ''),
                'date_posted': job.get('createdAt', ''),
                'source': 'lever',
                'raw_data': job
            })
            
            job_obj.sanitize()
            if job_obj.is_valid():
                normalized_jobs.append(job_obj.to_dict())
        
        logger.info(f"Fetched {len(normalized_jobs)} jobs from Lever for {company_name}")
        return normalized_jobs


class AshbyFetcher:
    """Async Fetcher for Ashby GraphQL API"""
    
    def __init__(self, client: SafeSession):
        self.client = client
    
    async def fetch_jobs(self, board_url: str, company_name: str, applied_ids: set) -> List[Dict[str, Any]]:
        """Fetch jobs from Ashby GraphQL API asynchronously"""
        if "ashbyhq.com" in board_url:
             company_slug = board_url.rstrip('/').split('/')[-1]
        else:
             company_slug = board_url

        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"
        
        jobs_data = await self.client.fetch_json(api_url)
        
        if not jobs_data:
            return []

        jobs = []
        if isinstance(jobs_data, dict):
            jobs = jobs_data.get('jobs', [])
        elif isinstance(jobs_data, list):
            jobs = jobs_data
            
        normalized_jobs = []
        for job in jobs:
            title = job.get('title', '').strip()
            location = job.get('location', job.get('locationName', ''))
            if not location:
                location = job.get('address', {}).get('placeName', '')
            
            job_id = f"ashby_{company_slug}_{job.get('id', job.get('jobId', ''))}"

            # Order of Operations: Applied Check FIRST
            is_applied = job_id in applied_ids
            
            if not is_applied:
                # Gatekeeper: Structural Quality
                job_payload = {
                    'title': title,
                    'location': location,
                    'date_posted': job.get('publishedDate', job.get('createdAt', ''))
                }
                if not job_filter.passes_hard_filters(job_payload):
                    continue

            job_obj = JobListing.from_dict({
                'id': job_id,
                'title': title,
                'company': company_name,
                'location': location,
                'url': job.get('jobUrl', f"{board_url}/{job.get('id', '')}"),
                'description': job.get('description', job.get('descriptionHtml', '')),
                'date_posted': job.get('publishedDate', job.get('createdAt', '')),
                'source': 'ashby',
                'raw_data': job
            })
            
            job_obj.sanitize()
            if job_obj.is_valid():
                normalized_jobs.append(job_obj.to_dict())
        
        logger.info(f"Fetched {len(normalized_jobs)} jobs from Ashby for {company_name}")
        return normalized_jobs


class JobFetcherManager:
    """Manages all job fetchers with concurrency control"""
    
    def __init__(self):
        # LIMIT CONCURRENCY via Config
        # We need to peek at the config here or use a safe default
        # Since we don't have the client session yet, we can check the file directly 
        # or just use the default.
        # Ideally, we should use the same source of truth.
        try:
            import yaml
            config_path = BASE_DIR / "config" / "filtering.yaml"
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)
                limit = data.get("system", {}).get("concurrency_limit", 5)
        except:
            limit = 5
            
        self.semaphore = asyncio.Semaphore(limit)
    
    async def fetch_all_jobs(self, companies_config: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetch jobs from all configured companies concurrently"""
        
        # Load applied IDs once to pass down to fetchers
        applied_ids = set()
        applied_path = BASE_DIR / 'data' / 'applied_jobs.json'
        if applied_path.exists():
            try:
                with open(applied_path, 'r', encoding='utf-8') as f:
                    applied_data = json.load(f)
                    applied_ids = {j['id'] for j in applied_data if 'id' in j}
            except Exception as e:
                logger.error(f"Error loading applied IDs for fetcher: {e}")

        async with aiohttp.ClientSession() as session:
            safe_client = SafeSession(session)
            
            # Instantiate fetchers
            greenhouse = GreenhouseFetcher(safe_client)
            lever = LeverFetcher(safe_client)
            ashby = AshbyFetcher(safe_client)
            
            tasks = []
            for company in companies_config:
                tasks.append(self._bounded_fetch(
                    company, 
                    greenhouse, lever, ashby,
                    applied_ids
                ))
            
            # Run all fetch tasks
            logger.info(f"Starting async fetch for {len(companies_config)} companies...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Flatten results
            all_jobs = []
            for res in results:
                if isinstance(res, list):
                    all_jobs.extend(res)
                elif isinstance(res, Exception):
                    logger.error(f"Task failed with exception: {res}")
            
            logger.info(f"Total jobs ingested: {len(all_jobs)}")
            return all_jobs

    async def _bounded_fetch(self, company: Dict[str, Any], gh, lev, ash, applied_ids: set) -> List[Dict[str, Any]]:
        """
        Acquires a semaphore lock before making the network request.
        """
        company_name = company.get('name')
        ats_type = company.get('ats', '').lower()
        
        async with self.semaphore:
            try:
                if ats_type == 'greenhouse':
                    board_token = company.get('board_token') or company.get('token')
                    if board_token:
                        results = await gh.fetch_jobs(board_token, company_name, applied_ids)
                    else:
                        results = []
                
                elif ats_type == 'lever':
                    board_token = company.get('board_token') or company.get('token')
                    if board_token:
                        results = await lev.fetch_jobs(board_token, company_name, applied_ids)
                    else:
                        results = []
                
                elif ats_type == 'ashby':
                    scraping_url = company.get('board_url', company.get('url'))
                    if scraping_url:
                        results = await ash.fetch_jobs(scraping_url, company_name, applied_ids)
                    else:
                        results = []
                
                else:
                    logger.warning(f"Unknown ATS type '{ats_type}' for {company_name}")
                    return []

                # Enrich results with company-level UI info
                for job in results:
                    job['job_board_url'] = company.get('job_board_url')
                    job['careers_page'] = company.get('careers_page')
                    job['enrichment'] = company.get('enrichment')
                
                return results
                    
            except Exception as e:
                logger.error(f"Error fetching {company_name}: {e}")
                return []
            
            return []
