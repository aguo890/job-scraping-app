from dataclasses import dataclass, asdict
import logging
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

@dataclass
class JobListing:
    id: str
    title: str
    company: str
    url: str
    location: Optional[str] = "Remote"
    description: Optional[str] = ""
    date_posted: Optional[str] = ""
    source: Optional[str] = "Unknown"
    score: float = 0.0
    match_reason: Optional[str] = ""
    raw_data: Optional[Dict[str, Any]] = None

    def is_valid(self) -> bool:
        """Check for required fields and log if missing to prevent silent data loss."""
        required_fields = ["id", "title", "company", "url"]
        missing = [f for f in required_fields if not getattr(self, f)]
        
        if missing:
            logger.warning(f"Validation Failed - Dropped Job Record. Missing fields: {missing}. Data: {self.id} | {self.title}")
            return False
        return True
        
    def sanitize(self):
        """Clean up whitespace and remove HTML tags from critical fields."""
        def clean_html(text: str) -> str:
            if not text: return ""
            # Basic HTML stripping
            clean = re.sub('<[^<]+?>', '', text)
            return clean.replace('\n', ' ').strip()

        self.title = clean_html(self.title)
        self.company = clean_html(self.company)
        self.location = clean_html(self.location) if self.location else "Remote"
        
        if self.description:
            self.description = clean_html(self.description)
            
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
