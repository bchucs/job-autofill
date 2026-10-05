"""Form auto-filling using Playwright browser automation."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    from playwright.sync_api import Page, sync_playwright, Browser, BrowserContext
except ImportError:
    sync_playwright = None
    Page = None
    Browser = None
    BrowserContext = None


@dataclass
class FieldMapping:
    """Maps form field selectors to profile data."""

    selector: str
    value: Any
    field_type: str = "text"  # text, select, checkbox, radio, file
    label: str = ""


@dataclass
class FormAnalysis:
    """Analysis of a job application form."""

    url: str
    platform: Optional[str] = None
    fields: list[FieldMapping] = field(default_factory=list)
    file_uploads: list[dict] = field(default_factory=list)
    submit_button: Optional[str] = None
    requires_login: bool = False
    error_messages: list[str] = field(default_factory=list)


class FormFiller:
    """Automates form filling using Playwright."""

    # Expanded field patterns for comprehensive matching
    FIELD_PATTERNS = {
        # Basic info
        "first_name": [
            r"first[_\s-]?name", r"fname", r"given[_\s-]?name", r"name.*first",
        ],
        "last_name": [
            r"last[_\s-]?name", r"lname", r"surname", r"family[_\s-]?name", r"name.*last",
        ],
        "full_name": [
            r"full[_\s-]?name", r"^name$", r"your[_\s-]?name",
        ],
        "email": [
            r"e?-?mail", r"email[_\s-]?address",
        ],
        "phone": [
            r"phone[_\s-]?(number)?$", r"mobile", r"tel$", r"cell", r"contact[_\s-]?number",
        ],
        "phone_country_code": [
            r"country[_\s-]?code", r"phone.*code", r"dial", r"calling[_\s-]?code",
        ],

        # Address
        "address_street": [
            r"street", r"address[_\s-]?line[_\s-]?1", r"^address$", r"address1",
        ],
        "address_city": [
            r"city", r"town", r"locality",
        ],
        "address_state": [
            r"state", r"province", r"region",
        ],
        "address_zip": [
            r"zip", r"postal", r"postcode",
        ],
        "address_country": [
            r"country",
        ],

        # Professional links
        "linkedin": [
            r"linkedin", r"linked[_\s-]?in",
        ],
        "github": [
            r"github", r"git[_\s-]?hub",
        ],
        "portfolio": [
            r"portfolio", r"website", r"personal[_\s-]?(site|website|url)", r"^url$",
        ],

        # Education - University
        "education_school": [
            r"school", r"university", r"college", r"institution",
        ],
        "education_degree": [
            r"degree", r"^degree[_\s-]?type",
        ],
        "education_major": [
            r"major", r"field[_\s-]?of[_\s-]?study", r"discipline", r"concentration", r"area[_\s-]?of[_\s-]?study",
        ],
        "education_gpa": [
            r"gpa", r"grade[_\s-]?point", r"cumulative",
        ],
        "education_start_date": [
            r"(education|school|university).*(start|from|begin)", r"start.*(date|year|month).*education",
        ],
        "education_end_date": [
            r"(education|school|university).*(end|to|graduation|graduate)", r"end.*(date|year|month).*education",
            r"graduation[_\s-]?(date|year|month)", r"expected[_\s-]?graduation", r"grad[_\s-]?(date|year)",
        ],
        "education_start_year": [
            r"start[_\s-]?year", r"from[_\s-]?year", r"begin[_\s-]?year",
        ],
        "education_end_year": [
            r"end[_\s-]?year", r"graduation[_\s-]?year", r"to[_\s-]?year",
        ],
        "education_start_month": [
            r"start[_\s-]?month", r"from[_\s-]?month",
        ],
        "education_end_month": [
            r"end[_\s-]?month", r"graduation[_\s-]?month", r"to[_\s-]?month",
        ],

        # High school
        "high_school_name": [
            r"high[_\s-]?school", r"secondary[_\s-]?school",
        ],
        "high_school_graduation": [
            r"high[_\s-]?school.*(grad|year|date)", r"secondary.*(grad|year)",
        ],

        # Standardized tests
        "sat_score": [
            r"sat[_\s-]?(score|total)?$",
        ],
        "act_score": [
            r"act[_\s-]?(score|total)?$",
        ],
        "gre_score": [
            r"gre[_\s-]?(score|total)?$",
        ],
        "test_score": [
            r"standardized[_\s-]?test", r"test[_\s-]?score",
        ],

        # Work authorization
        "authorized_to_work": [
            r"authorized[_\s-]?to[_\s-]?work", r"legally[_\s-]?(authorized|eligible|permitted)",
            r"eligible[_\s-]?to[_\s-]?work", r"work[_\s-]?authorization", r"right[_\s-]?to[_\s-]?work",
        ],
        "requires_sponsorship": [
            r"sponsor", r"visa[_\s-]?(sponsor|support)", r"immigration[_\s-]?sponsor",
            r"require.*sponsor", r"need.*sponsor", r"sponsorship",
        ],
        "citizenship": [
            r"citizenship", r"citizen", r"nationality",
        ],

        # Application-specific questions
        "applied_before": [
            r"applied[_\s-]?(before|previously)", r"previous[_\s-]?application",
            r"have[_\s-]?you[_\s-]?applied", r"applied[_\s-]?to[_\s-]?(this|another|other)[_\s-]?role",
        ],
        "other_offers": [
            r"other[_\s-]?offer", r"competing[_\s-]?offer", r"have[_\s-]?(any)?[_\s-]?offer",
            r"received[_\s-]?(any)?[_\s-]?offer",
        ],
        "referral": [
            r"referr", r"hear[_\s-]?about", r"how[_\s-]?did[_\s-]?you[_\s-]?(hear|find|learn)",
            r"source", r"referred[_\s-]?by",
        ],
        "salary_expectation": [
            r"salary", r"compensation", r"pay[_\s-]?expectation", r"expected[_\s-]?(salary|pay|compensation)",
        ],
        "start_date_available": [
            r"(available|earliest)[_\s-]?(start|begin)", r"when[_\s-]?can[_\s-]?you[_\s-]?start",
            r"start[_\s-]?date[_\s-]?available", r"availability",
        ],

        # EEOC / Demographics
        "gender": [
            r"gender", r"sex$",
        ],
        "race_ethnicity": [
            r"race", r"ethnicity", r"ethnic",
        ],
        "veteran_status": [
            r"veteran", r"military[_\s-]?service",
        ],
        "disability_status": [
            r"disability", r"disabled", r"accommodation",
        ],

        # Documents
        "resume": [
            r"resume", r"cv", r"curriculum",
        ],
        "cover_letter": [
            r"cover[_\s-]?letter", r"motivation[_\s-]?letter",
        ],
    }

    def __init__(self, profile: dict, headless: bool = False, cdp_url: str = None):
        self.profile = profile
        self.headless = headless
        self.cdp_url = cdp_url  # For connecting to existing browser
        self._browser: Optional["Browser"] = None
        self._context: Optional["BrowserContext"] = None
        self._page: Optional["Page"] = None
        self._owns_browser = True  # Whether we launched the browser

    def _ensure_playwright(self) -> None:
        """Ensure Playwright is available."""
        if sync_playwright is None:
            raise ImportError(
                "playwright is required. Install with:\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )

    def connect_to_browser(self, cdp_url: str = "http://localhost:9222") -> bool:
        """Connect to an existing Chrome browser via CDP.

        Start Chrome with:
          /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222
        """
        self._ensure_playwright()
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.connect_over_cdp(cdp_url)
            contexts = self._browser.contexts
            if contexts:
                self._context = contexts[0]
                pages = self._context.pages
                if pages:
                    self._page = pages[0]  # Use first tab
            self._owns_browser = False
            return True
        except Exception as e:
            print(f"Failed to connect to browser: {e}")
            print("Make sure Chrome is running with --remote-debugging-port=9222")
            return False

    def start_browser(self) -> None:
        """Start a new browser."""
        self._ensure_playwright()
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = self._context.new_page()
        self._owns_browser = True

    def stop_browser(self) -> None:
        """Stop the browser (only if we own it)."""
        if self._owns_browser:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
        if hasattr(self, "_playwright") and self._playwright:
            self._playwright.stop()

    def navigate_to(self, url: str) -> None:
        """Navigate to a URL."""
        if not self._page:
            self.start_browser()
        self._page.goto(url, wait_until="networkidle")

    def analyze_current_page(self) -> FormAnalysis:
        """Analyze the current page (for use with connected browser)."""
        if not self._page:
            raise RuntimeError("No page available. Connect to browser first.")

        analysis = FormAnalysis(url=self._page.url)
        analysis.platform = self._detect_platform()
        analysis.requires_login = self._check_login_required()

        if not analysis.requires_login:
            analysis.fields = self._find_fillable_fields()
            analysis.file_uploads = self._find_file_uploads()
            analysis.submit_button = self._find_submit_button()

        return analysis

    def analyze_form(self, url: str) -> FormAnalysis:
        """Analyze a job application form and identify fillable fields."""
        self.navigate_to(url)
        return self.analyze_current_page()

    def _detect_platform(self) -> Optional[str]:
        """Detect the ATS platform from page content."""
        url = self._page.url.lower()
        content = self._page.content().lower()

        platform_markers = {
            "greenhouse": ["greenhouse", "boards.greenhouse.io"],
            "lever": ["lever.co", "lever-jobs"],
            "workday": ["workday", "myworkdayjobs"],
            "icims": ["icims"],
            "ashby": ["ashbyhq", "ashby"],
            "bamboohr": ["bamboohr"],
            "smartrecruiters": ["smartrecruiters"],
            "jobvite": ["jobvite"],
        }

        for platform, markers in platform_markers.items():
            for marker in markers:
                if marker in url or marker in content:
                    return platform

        return None

    def _check_login_required(self) -> bool:
        """Check if the page requires login."""
        login_indicators = [
            "input[type='password']",
            "button:text('Sign in')",
            "button:text('Log in')",
            "a:text('Sign in')",
            "a:text('Log in')",
            ".login-form",
            "#login",
        ]

        for indicator in login_indicators:
            try:
                if self._page.locator(indicator).count() > 0:
                    if "apply" not in self._page.url.lower():
                        return True
            except Exception:
                continue

        return False

    def _find_fillable_fields(self) -> list[FieldMapping]:
        """Find all fillable form fields and map to profile data."""
        fields = []

        # Find all input fields
        inputs = self._page.locator(
            "input[type='text'], input[type='email'], input[type='tel'], "
            "input[type='url'], input[type='number'], input:not([type]), textarea"
        )

        for i in range(inputs.count()):
            try:
                element = inputs.nth(i)
                if not element.is_visible():
                    continue
                mapping = self._map_input_field(element)
                if mapping:
                    fields.append(mapping)
            except Exception:
                continue

        # Find select fields
        selects = self._page.locator("select")
        for i in range(selects.count()):
            try:
                element = selects.nth(i)
                if not element.is_visible():
                    continue
                mapping = self._map_select_field(element)
                if mapping:
                    fields.append(mapping)
            except Exception:
                continue

        return fields

    def _map_input_field(self, element) -> Optional[FieldMapping]:
        """Map an input field to profile data."""
        try:
            name = element.get_attribute("name") or ""
            id_attr = element.get_attribute("id") or ""
            placeholder = element.get_attribute("placeholder") or ""
            aria_label = element.get_attribute("aria-label") or ""
            label_text = self._get_label_text(element)

            # Combine all identifiers for matching
            identifiers = f"{name} {id_attr} {placeholder} {aria_label} {label_text}".lower()

            # Try to match to a profile field
            for profile_key, patterns in self.FIELD_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, identifiers, re.IGNORECASE):
                        value = self._get_profile_value(profile_key)
                        if value is not None:
                            selector = self._get_unique_selector(element)
                            if selector:
                                return FieldMapping(
                                    selector=selector,
                                    value=value,
                                    field_type="text",
                                    label=label_text or placeholder or name,
                                )
                        break

        except Exception:
            pass

        return None

    def _map_select_field(self, element) -> Optional[FieldMapping]:
        """Map a select field to profile data."""
        try:
            name = element.get_attribute("name") or ""
            id_attr = element.get_attribute("id") or ""
            aria_label = element.get_attribute("aria-label") or ""
            label_text = self._get_label_text(element)

            identifiers = f"{name} {id_attr} {aria_label} {label_text}".lower()

            # Map various select fields
            select_mappings = [
                (r"country[_\s-]?code|dial|calling", "phone_country_code"),
                (r"country", "address_country"),
                (r"state|province", "address_state"),
                (r"degree", "education_degree"),
                (r"major|discipline|field[_\s-]?of[_\s-]?study", "education_major"),
                (r"gender|sex", "gender"),
                (r"race|ethnic", "race_ethnicity"),
                (r"veteran", "veteran_status"),
                (r"disability", "disability_status"),
                (r"sponsor", "requires_sponsorship"),
                (r"authorized|eligible.*work|work.*authorization", "authorized_to_work"),
                (r"graduation[_\s-]?(year|month|date)", "education_end_date"),
                (r"start[_\s-]?(year|month)", "education_start_year"),
                (r"end[_\s-]?(year|month)", "education_end_year"),
            ]

            for pattern, profile_key in select_mappings:
                if re.search(pattern, identifiers, re.IGNORECASE):
                    value = self._get_profile_value(profile_key)
                    if value is not None:
                        selector = self._get_unique_selector(element)
                        if selector:
                            return FieldMapping(
                                selector=selector,
                                value=value,
                                field_type="select",
                                label=label_text or name,
                            )
                    break

        except Exception:
            pass

        return None

    def _get_label_text(self, element) -> str:
        """Get the label text associated with an input element."""
        try:
            # Try to find label by 'for' attribute
            element_id = element.get_attribute("id")
            if element_id:
                label = self._page.locator(f"label[for='{element_id}']")
                if label.count() > 0:
                    return label.first.inner_text()

            # Try parent label
            parent_label = element.locator("xpath=ancestor::label")
            if parent_label.count() > 0:
                return parent_label.first.inner_text()

            # Try nearby label (previous sibling or parent's previous sibling)
            nearby = element.locator("xpath=preceding-sibling::label[1]")
            if nearby.count() > 0:
                return nearby.first.inner_text()

        except Exception:
            pass

        return ""

    def _get_unique_selector(self, element) -> str:
        """Generate a unique CSS selector for an element."""
        try:
            element_id = element.get_attribute("id")
            if element_id:
                return f"#{element_id}"

            name = element.get_attribute("name")
            if name:
                tag = element.evaluate("el => el.tagName.toLowerCase()")
                return f"{tag}[name='{name}']"

            # Try data attributes
            data_test = element.get_attribute("data-testid")
            if data_test:
                return f"[data-testid='{data_test}']"

        except Exception:
            pass

        return ""

    def _get_profile_value(self, key: str) -> Optional[str]:
        """Get a value from the profile by key."""
        # Address fields
        if key.startswith("address_"):
            addr_key = key.replace("address_", "")
            return self.profile.get("address", {}).get(addr_key)

        # Education fields
        if key.startswith("education_"):
            edu_key = key.replace("education_", "")
            education = self.profile.get("education", [])
            if education:
                edu = education[0]  # Use first education entry
                if edu_key == "school":
                    return edu.get("school")
                elif edu_key == "degree":
                    return edu.get("degree")
                elif edu_key == "major":
                    return edu.get("major")
                elif edu_key == "gpa":
                    return edu.get("gpa")
                elif edu_key in ("end_date", "graduation"):
                    return edu.get("graduation_date")
                elif edu_key == "end_year":
                    grad = edu.get("graduation_date", "")
                    if grad:
                        return grad.split("-")[0]  # Extract year
                elif edu_key == "end_month":
                    grad = edu.get("graduation_date", "")
                    if "-" in grad:
                        return grad.split("-")[1]  # Extract month
                elif edu_key == "start_year":
                    return edu.get("start_year", "")
                elif edu_key == "start_date":
                    return edu.get("start_date", "")
            return None

        # High school fields
        if key.startswith("high_school_"):
            hs = self.profile.get("high_school", {})
            hs_key = key.replace("high_school_", "")
            return hs.get(hs_key)

        # Test scores
        if key in ("sat_score", "act_score", "gre_score", "test_score"):
            tests = self.profile.get("test_scores", {})
            return tests.get(key.replace("_score", ""))

        # Work authorization
        if key == "authorized_to_work":
            auth = self.profile.get("authorized_to_work")
            return "Yes" if auth else "No"

        if key == "requires_sponsorship":
            sponsor = self.profile.get("requires_sponsorship")
            return "Yes" if sponsor else "No"

        # Yes/No questions
        if key == "applied_before":
            val = self.profile.get("applied_before")
            if val is not None:
                return "Yes" if val else "No"
            return "No"

        if key == "other_offers":
            val = self.profile.get("other_offers")
            if val is not None:
                return "Yes" if val else "No"
            return None

        # Full name
        if key == "full_name":
            first = self.profile.get("first_name", "")
            last = self.profile.get("last_name", "")
            if first and last:
                return f"{first} {last}"
            return None

        # Phone country code
        if key == "phone_country_code":
            return self.profile.get("phone_country_code", "+1")

        # Direct profile fields
        return self.profile.get(key)

    def _find_file_uploads(self) -> list[dict]:
        """Find file upload fields."""
        uploads = []
        file_inputs = self._page.locator("input[type='file']")

        for i in range(file_inputs.count()):
            element = file_inputs.nth(i)
            try:
                name = element.get_attribute("name") or ""
                accept = element.get_attribute("accept") or ""
                label_text = self._get_label_text(element)

                identifiers = f"{name} {label_text}".lower()

                upload_type = "other"
                file_path = None

                if re.search(r"resume|cv", identifiers):
                    upload_type = "resume"
                    file_path = self.profile.get("resume_path")
                elif re.search(r"cover", identifiers):
                    upload_type = "cover_letter"
                    file_path = self.profile.get("cover_letter_path")

                uploads.append({
                    "selector": self._get_unique_selector(element),
                    "type": upload_type,
                    "file_path": file_path,
                    "accept": accept,
                    "label": label_text,
                })

            except Exception:
                continue

        return uploads

    def _find_submit_button(self) -> Optional[str]:
        """Find the submit button."""
        submit_patterns = [
            "button[type='submit']",
            "input[type='submit']",
            "button:text('Submit')",
            "button:text('Apply')",
            "button:text('Send')",
            "button:text('Continue')",
            "button:text('Next')",
        ]

        for pattern in submit_patterns:
            try:
                if self._page.locator(pattern).count() > 0:
                    return pattern
            except Exception:
                continue

        return None

    def fill_form(self, analysis: FormAnalysis = None, dry_run: bool = True) -> dict:
        """Fill the form based on analysis. Returns filled fields info."""
        if analysis is None:
            analysis = self.analyze_current_page()

        filled = {"fields": [], "files": [], "errors": []}

        if analysis.requires_login:
            filled["errors"].append("Cannot fill form: login required")
            return filled

        # Fill text fields
        for fld in analysis.fields:
            try:
                if fld.field_type == "text":
                    if not dry_run:
                        self._page.fill(fld.selector, str(fld.value))
                    filled["fields"].append({
                        "selector": fld.selector,
                        "value": fld.value,
                        "label": fld.label,
                        "status": "filled" if not dry_run else "would_fill",
                    })
                elif fld.field_type == "select":
                    if not dry_run:
                        try:
                            self._page.select_option(fld.selector, label=str(fld.value))
                        except Exception:
                            # Try by value
                            self._page.select_option(fld.selector, value=str(fld.value))
                    filled["fields"].append({
                        "selector": fld.selector,
                        "value": fld.value,
                        "label": fld.label,
                        "status": "selected" if not dry_run else "would_select",
                    })
            except Exception as e:
                filled["errors"].append(f"Failed to fill {fld.label or fld.selector}: {e}")

        # Handle file uploads
        for upload in analysis.file_uploads:
            if upload["file_path"] and os.path.exists(upload["file_path"]):
                try:
                    if not dry_run:
                        self._page.set_input_files(
                            upload["selector"],
                            upload["file_path"],
                        )
                    filled["files"].append({
                        "type": upload["type"],
                        "file": upload["file_path"],
                        "status": "uploaded" if not dry_run else "would_upload",
                    })
                except Exception as e:
                    filled["errors"].append(f"Failed to upload {upload['type']}: {e}")
            elif upload["file_path"]:
                filled["errors"].append(
                    f"File not found: {upload['file_path']} for {upload['type']}"
                )

        return filled

    def fill_current_page(self, dry_run: bool = False) -> dict:
        """Convenience method to analyze and fill the current page."""
        analysis = self.analyze_current_page()
        return self.fill_form(analysis, dry_run=dry_run)

    def submit_form(self, analysis: FormAnalysis) -> bool:
        """Submit the form. Returns True if successful."""
        if not analysis.submit_button:
            return False

        try:
            self._page.click(analysis.submit_button)
            self._page.wait_for_load_state("networkidle", timeout=10000)
            return True
        except Exception:
            return False

    def take_screenshot(self, path: str) -> None:
        """Take a screenshot of the current page."""
        if self._page:
            self._page.screenshot(path=path)

    def get_page_content(self) -> str:
        """Get the current page content."""
        if self._page:
            return self._page.content()
        return ""

    def wait_for_user_action(self) -> None:
        """Pause for user to interact with the page manually."""
        if self._page:
            input("Press Enter when ready to continue...")
