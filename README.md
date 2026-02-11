# Job Scraping Application

An advanced job scraping tool that automatically fetches, processes, and analyzes job postings from multiple ATS platforms (Greenhouse, Lever, Ashby).

> ℹ️ **Fork Information:** This is an enhanced fork of [billyweinberger/job-scraping-app](https://github.com/billyweinberger/job-scraping-app). It includes advanced filtering, interactive dashboards, and optimized processing logic.

## ✨ Key Enhancements (New in this Fork)

### 📊 Interactive Dashboard
- **Smart Sidebar:** Filter by Status (Applied/Rejected), Date Range, Match Score, and Keywords.
- **Job Actions:** Save jobs, update status (Interviewing, Offer), and "Hide Rejected" toggle.
- **Visuals:** Status emojis (⭐, 🎤, ✅), score progress bars, and responsive layout.

### 🧠 Improved Processor
- **"Early Bird" Boost:** Score bonus for jobs posted within the last 24 hours.
- **Data Reliability:** Auto-fix for missing dates; persistent state tracking via `tracking.json`.
- **Dockerized:** One-command setup.

## Features

- **Multi-Platform Fetching**: Scrapes jobs from:
  - Greenhouse API (`https://boards-api.greenhouse.io`)
  - Lever API (`https://api.lever.co`)
  - Ashby GraphQL (`jobs.ashbyhq.com`)

- **Intelligent Processing**:
  - Data normalization across different ATS formats
  - Deduplication based on job title and company
  - Ranking system based on configurable keywords and skills
  - Location normalization

- **AI Integration** (Optional):
  - Job description analysis using ChatGPT
  - Resume tailoring tips
  - Cover letter outline generation
  - Interview preparation guidance

- **Automated Reporting**:
  - JSON output (`data/jobs_agg.json`)
  - Markdown daily reports (`report/YYYY-MM-DD.md`)
  - Automatic GitHub commits
  - Daily digest GitHub issues

- **Applied Job Tracking**:
  - Persist jobs you've applied to forever
  - Mark jobs with `mark_applied.py`
  - Applied jobs are highlighted with ✅ and kept at the top of reports
  - "Ghost Jobs" (applied but removed from internet) are preserved

- **GitHub Actions Integration**:
  - Runs daily at 9 AM UTC
  - Manual trigger support
  - Automatic artifact upload

## Setup

### 1. Prerequisites

- Python 3.11+
- GitHub repository with Actions enabled
- (Optional) OpenAI API key for AI features

## 🐳 Quick Start (Docker)

The easiest way to run the dashboard is using Docker.

1. **Prerequisites:** Ensure Docker and Make are installed.
2. **Run:**
   ```bash
   make app
   ```
   *This builds the image and launches the dashboard on `http://localhost:8501`.*

### 2. Installation

```bash
pip install -r requirements.txt
```

### 3. Configuration

#### Companies Configuration (`config/companies.yaml`)

Define companies to scrape:

```yaml
companies:
  - name: "OpenAI"
    ats: "greenhouse"
    board_token: "openai"
  
  - name: "Stripe"
    ats: "greenhouse"
    board_token: "stripe"
```

#### Keywords Configuration (`config/keywords.yaml`)

Configure job filtering and ranking:

```yaml
keywords:
  high_priority:
    - "Senior Software Engineer"
    - "Staff Engineer"
  
preferred_skills:
  - "Python"
  - "React"
```

### 4. GitHub Secrets

Configure these secrets in your repository:

- `GITHUB_TOKEN`: Automatically provided by GitHub Actions (no setup needed)
- `OPENAI_API_KEY`: (Optional) Your OpenAI API key for AI features

## Usage

### Manual Run

```bash
python main.py
```

### GitHub Actions

The workflow runs automatically daily at 9 AM UTC. You can also trigger it manually from the Actions tab.

## Output

### JSON Output (`data/jobs_agg.json`)

Contains all processed jobs with metadata:

```json
{
  "generated_at": "2024-01-15T09:00:00",
  "total_jobs": 150,
  "jobs": [
    {
      "id": "gh_openai_12345",
      "title": "Senior Software Engineer",
      "company": "OpenAI",
      "location": "San Francisco, CA",
      "score": 25.0,
      "url": "https://...",
      ...
    }
  ]
}
```

### Markdown Report (`report/YYYY-MM-DD.md`)

Human-readable daily report with:
- Summary statistics
- Top job opportunities (ranked by score)
- Jobs grouped by company

### GitHub Issue

Automatically creates/updates a "Daily Roles Digest" issue with:
- Summary of jobs found
- Top 10 opportunities
- Links to full reports

## Architecture

```
┌─────────────────────┐
│  GitHub Actions     │
│  (Daily Schedule)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    main.py          │
│  (Orchestrator)     │
└──────────┬──────────┘
           │
    ┌──────┴──────┬──────────────┬─────────────┐
    ▼             ▼              ▼             ▼
┌────────┐  ┌───────────┐  ┌──────────┐  ┌─────────┐
│Fetchers│  │ Processor │  │ Reporter │  │   AI    │
└────────┘  └───────────┘  └──────────┘  └─────────┘
│           │              │             │
│ Greenhouse│ Normalize    │ JSON        │ Analysis
│ Lever     │ Deduplicate  │ Markdown    │ Resume Tips
│ Ashby     │ Rank         │             │ Interview
└───────────┴──────────────┴─────────────┴──────────
                           │
                           ▼
                  ┌─────────────────┐
                  │ GitHub Integration│
                  │ - Commit/Push   │
                  │ - Create Issues │
                  └─────────────────┘
```

## Modules

- **`fetchers.py`**: Job fetchers for different ATS platforms
- **`processor.py`**: Data normalization, deduplication, and ranking
- **`reporter.py`**: Output generation (JSON and Markdown)
- **`github_integration.py`**: GitHub commits and issue management
- **`ai_assistant.py`**: ChatGPT integration for job analysis
- **`main.py`**: Main orchestration script

## Logging

Logs are stored in `logs/job_scraping_YYYY-MM-DD.log` with detailed information about:
- Fetching progress
- Processing steps
- Errors and warnings
- API calls

## Error Handling

The application includes comprehensive error handling:
- API request failures are logged and don't stop execution
- Missing configuration files raise clear errors
- GitHub operations gracefully handle missing tokens
- AI features degrade gracefully when API key is not configured

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License
