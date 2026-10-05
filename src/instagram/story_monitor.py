"""Instagram story monitoring using instaloader."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

try:
    import instaloader
except ImportError:
    instaloader = None


@dataclass
class StoryItem:
    """Represents a single story item with extracted data."""

    story_id: str
    account: str
    timestamp: datetime
    urls: list[str]
    caption: Optional[str] = None
    is_video: bool = False


class StoryMonitor:
    """Monitors Instagram stories for target accounts."""

    def __init__(self, username: str, password: str, target_accounts: list[str]):
        self.username = username
        self.password = password
        self.target_accounts = target_accounts
        self._loader: Optional["instaloader.Instaloader"] = None
        self._logged_in = False

    def _ensure_instaloader(self) -> None:
        """Ensure instaloader is available."""
        if instaloader is None:
            raise ImportError(
                "instaloader is required. Install with: pip install instaloader"
            )

    def _get_loader(self) -> "instaloader.Instaloader":
        """Get or create instaloader instance."""
        self._ensure_instaloader()
        if self._loader is None:
            self._loader = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
            )
        return self._loader

    def login(self) -> bool:
        """Log in to Instagram. Returns True if successful."""
        loader = self._get_loader()
        try:
            loader.login(self.username, self.password)
            self._logged_in = True
            return True
        except instaloader.exceptions.BadCredentialsException:
            print("Error: Invalid Instagram credentials")
            return False
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            print("Error: Two-factor authentication required")
            print("Consider using session file or disabling 2FA temporarily")
            return False
        except instaloader.exceptions.ConnectionException as e:
            print(f"Error: Connection failed - {e}")
            return False

    def load_session(self, session_file: Optional[str] = None) -> bool:
        """Load a saved session to avoid repeated logins."""
        loader = self._get_loader()
        try:
            if session_file:
                loader.load_session_from_file(self.username, session_file)
            else:
                loader.load_session_from_file(self.username)
            self._logged_in = True
            return True
        except FileNotFoundError:
            return False

    def save_session(self, session_file: Optional[str] = None) -> None:
        """Save current session for future use."""
        loader = self._get_loader()
        if session_file:
            loader.save_session_to_file(session_file)
        else:
            loader.save_session_to_file()

    def check_connection(self) -> dict:
        """Verify Instagram connection and return status."""
        status = {
            "logged_in": self._logged_in,
            "username": self.username,
            "target_accounts": self.target_accounts,
            "accounts_accessible": [],
            "errors": [],
        }

        if not self._logged_in:
            status["errors"].append("Not logged in")
            return status

        loader = self._get_loader()
        for account in self.target_accounts:
            try:
                profile = instaloader.Profile.from_username(
                    loader.context, account
                )
                status["accounts_accessible"].append({
                    "username": account,
                    "followers": profile.followers,
                    "is_private": profile.is_private,
                })
            except instaloader.exceptions.ProfileNotExistsException:
                status["errors"].append(f"Account '{account}' not found")
            except Exception as e:
                status["errors"].append(f"Error accessing '{account}': {e}")

        return status

    def fetch_stories(self, account: Optional[str] = None) -> list[StoryItem]:
        """Fetch stories from target account(s)."""
        if not self._logged_in:
            raise RuntimeError("Must be logged in to fetch stories")

        accounts = [account] if account else self.target_accounts
        stories = []
        loader = self._get_loader()

        for target in accounts:
            try:
                profile = instaloader.Profile.from_username(
                    loader.context, target
                )
                for story in loader.get_stories(userids=[profile.userid]):
                    for item in story.get_items():
                        urls = self._extract_urls(item)
                        if urls:
                            stories.append(
                                StoryItem(
                                    story_id=str(item.mediaid),
                                    account=target,
                                    timestamp=item.date_utc,
                                    urls=urls,
                                    caption=item.caption if hasattr(item, "caption") else None,
                                    is_video=item.is_video,
                                )
                            )
            except instaloader.exceptions.LoginRequiredException:
                print(f"Login required to access stories from {target}")
            except Exception as e:
                print(f"Error fetching stories from {target}: {e}")

        return stories

    def _extract_urls(self, item) -> list[str]:
        """Extract URLs from a story item."""
        urls = []

        # Check for swipe-up link (story external URL)
        if hasattr(item, "url") and item.url:
            urls.append(item.url)

        # Check caption/text for URLs
        caption = ""
        if hasattr(item, "caption") and item.caption:
            caption = item.caption
        if hasattr(item, "caption_hashtags"):
            pass  # Hashtags handled separately if needed

        # Extract URLs from caption text
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        found_urls = re.findall(url_pattern, caption)
        urls.extend(found_urls)

        return list(set(urls))  # Remove duplicates


class ManualStoryInput:
    """Fallback for manual story link/URL input when API access fails."""

    def __init__(self):
        self.items: list[StoryItem] = []

    def add_url(self, url: str, account: str = "manual") -> StoryItem:
        """Manually add a URL found from a story."""
        item = StoryItem(
            story_id=f"manual_{datetime.now().timestamp()}",
            account=account,
            timestamp=datetime.now(),
            urls=[url],
        )
        self.items.append(item)
        return item

    def add_urls_from_text(self, text: str, account: str = "manual") -> list[StoryItem]:
        """Extract and add all URLs from pasted text."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        items = []
        for url in urls:
            items.append(self.add_url(url, account))
        return items

    def get_items(self) -> list[StoryItem]:
        """Get all manually added items."""
        return self.items

    def clear(self) -> None:
        """Clear all items."""
        self.items = []
