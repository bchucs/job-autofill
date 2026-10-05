"""Link extraction and URL resolution utilities."""

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests


@dataclass
class ResolvedLink:
    """Represents a resolved URL with metadata."""

    original_url: str
    final_url: str
    platform: Optional[str] = None
    company_hint: Optional[str] = None
    is_job_link: bool = False


class LinkExtractor:
    """Extracts and resolves URLs from various sources."""

    # Known URL shorteners
    SHORTENERS = [
        "bit.ly",
        "tinyurl.com",
        "t.co",
        "goo.gl",
        "ow.ly",
        "buff.ly",
        "is.gd",
        "v.gd",
        "soo.gd",
        "linktr.ee",
        "lnkd.in",
    ]

    # Known ATS platforms with their URL patterns
    ATS_PLATFORMS = {
        "greenhouse": [
            r"boards\.greenhouse\.io",
            r"job-boards\.greenhouse\.io",
            r".*\.greenhouse\.io",
        ],
        "lever": [
            r"jobs\.lever\.co",
            r".*\.lever\.co",
        ],
        "workday": [
            r".*\.myworkdayjobs\.com",
            r".*\.wd\d+\.myworkdayjobs\.com",
        ],
        "icims": [
            r".*\.icims\.com",
            r"careers-.*\.icims\.com",
        ],
        "ashby": [
            r"jobs\.ashbyhq\.com",
            r".*\.ashbyhq\.com",
        ],
        "bamboohr": [
            r".*\.bamboohr\.com/careers",
            r".*\.bamboohr\.com/jobs",
        ],
        "smartrecruiters": [
            r"jobs\.smartrecruiters\.com",
        ],
        "jobvite": [
            r"jobs\.jobvite\.com",
            r".*\.jobvite\.com",
        ],
        "breezy": [
            r".*\.breezy\.hr",
        ],
        "jazz": [
            r".*\.jazz\.co",
            r".*\.applytojob\.com",
        ],
    }

    # Job-related URL patterns
    JOB_PATTERNS = [
        r"/jobs?/",
        r"/careers?/",
        r"/apply",
        r"/positions?/",
        r"/openings?/",
        r"/opportunities?/",
        r"/internships?/",
        r"/hiring",
    ]

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

    def is_shortener(self, url: str) -> bool:
        """Check if URL is from a known shortener."""
        parsed = urlparse(url)
        return any(
            shortener in parsed.netloc.lower() for shortener in self.SHORTENERS
        )

    def resolve_url(self, url: str) -> str:
        """Resolve shortened URLs to their final destination."""
        try:
            response = self.session.head(
                url,
                allow_redirects=True,
                timeout=self.timeout,
            )
            return response.url
        except requests.exceptions.RequestException:
            # Try GET request as fallback
            try:
                response = self.session.get(
                    url,
                    allow_redirects=True,
                    timeout=self.timeout,
                    stream=True,  # Don't download body
                )
                response.close()
                return response.url
            except requests.exceptions.RequestException:
                return url

    def detect_platform(self, url: str) -> Optional[str]:
        """Detect ATS platform from URL."""
        for platform, patterns in self.ATS_PLATFORMS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return platform
        return None

    def is_job_link(self, url: str) -> bool:
        """Check if URL appears to be a job posting."""
        url_lower = url.lower()

        # Check ATS platforms
        if self.detect_platform(url):
            return True

        # Check job-related patterns
        for pattern in self.JOB_PATTERNS:
            if re.search(pattern, url_lower):
                return True

        return False

    def extract_company_hint(self, url: str) -> Optional[str]:
        """Try to extract company name from URL."""
        parsed = urlparse(url)
        platform = self.detect_platform(url)

        if platform == "greenhouse":
            # Format: boards.greenhouse.io/companyname
            match = re.search(r"greenhouse\.io/([^/]+)", parsed.path)
            if match:
                return match.group(1).replace("-", " ").title()

        elif platform == "lever":
            # Format: jobs.lever.co/companyname
            match = re.search(r"lever\.co/([^/]+)", parsed.path)
            if match:
                return match.group(1).replace("-", " ").title()

        elif platform == "workday":
            # Format: companyname.wd5.myworkdayjobs.com
            match = re.match(r"([^.]+)", parsed.netloc)
            if match and match.group(1) not in ["www", "careers"]:
                return match.group(1).replace("-", " ").title()

        elif platform == "ashby":
            # Format: jobs.ashbyhq.com/companyname
            match = re.search(r"ashbyhq\.com/([^/]+)", url)
            if match:
                return match.group(1).replace("-", " ").title()

        # Generic: try to get from subdomain
        parts = parsed.netloc.split(".")
        if len(parts) > 2 and parts[0] not in ["www", "jobs", "careers", "apply"]:
            return parts[0].replace("-", " ").title()

        return None

    def process_url(self, url: str) -> ResolvedLink:
        """Process a URL: resolve if shortened, detect platform, etc."""
        # Resolve shortened URLs
        final_url = url
        if self.is_shortener(url):
            final_url = self.resolve_url(url)

        # Detect platform and job status
        platform = self.detect_platform(final_url)
        is_job = self.is_job_link(final_url)
        company = self.extract_company_hint(final_url)

        return ResolvedLink(
            original_url=url,
            final_url=final_url,
            platform=platform,
            company_hint=company,
            is_job_link=is_job,
        )

    def extract_urls_from_text(self, text: str) -> list[str]:
        """Extract all URLs from a block of text."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return list(set(re.findall(url_pattern, text)))

    def filter_job_links(self, urls: list[str]) -> list[ResolvedLink]:
        """Process URLs and filter to only job-related links."""
        results = []
        for url in urls:
            resolved = self.process_url(url)
            if resolved.is_job_link:
                results.append(resolved)
        return results
