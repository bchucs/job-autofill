#!/usr/bin/env python3
"""
Local proxy server for Chrome extension to access Claude API.

Usage:
    ANTHROPIC_API_KEY=sk-... python server.py

The server listens on http://localhost:8765 and provides:
    GET  /health       - Check if server is running
    POST /match-fields - Match form fields to profile keys using Claude
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from pathlib import Path

PORT = 8765
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def load_api_key():
    """Load API key from environment or .env file."""
    # Check environment first
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key

    # Try loading from .env files
    env_paths = [
        Path(__file__).parent / ".env",           # extension/.env
        Path(__file__).parent.parent / ".env",    # project root/.env
        Path.home() / ".env",                     # ~/.env
    ]

    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        value = line.split("=", 1)[1].strip()
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        if value:
                            print(f"Loaded API key from {env_path}")
                            return value

    return ""


API_KEY = load_api_key()

SYSTEM_PROMPT = """You are a form field matcher for job applications. Given available profile keys and form fields extracted from a web page, determine which profile key should fill each field.

IMPORTANT RULES:
1. Only include fields you can CONFIDENTLY match to a profile key
2. Use null for fields that don't match any profile key or are ambiguous
3. For Yes/No questions, map to the boolean profile key (authorized_to_work, requires_sponsorship, etc.)
4. Match semantically - "Candidate Location (City)" should map to "address.city"
5. Be precise - don't guess if uncertain
6. CRITICAL FOR WORK EXPERIENCE: When you see multiple work experience sections (multiple Job Title, Company, Location fields), use INDEXED keys:
   - First set of work experience fields → experience.0.title, experience.0.company, etc.
   - Second set of work experience fields → experience.1.title, experience.1.company, etc.
   - Third set of work experience fields → experience.2.title, experience.2.company, etc.
   Use the field "index" number, IDs, or names containing numbers (like "workExperience-1", "workExperience-2") to determine which experience index to use.
   Fields with lower index numbers appear first on the page. Group fields by their proximity (similar index ranges = same work experience).

Return ONLY a JSON object mapping selector → profile_key. No explanation, no markdown."""

def build_prompt(profile_keys: list, fields: list) -> str:
    """Build the prompt for Claude to match fields."""
    fields_json = json.dumps(fields, indent=2)
    keys_list = "\n".join(f"- {key}" for key in profile_keys)

    return f"""AVAILABLE PROFILE KEYS:
{keys_list}

FORM FIELDS:
{fields_json}

Return a JSON object mapping each field's "selector" to the appropriate profile_key.
Example: {{"#first_name": "first_name", "#city": "address.city", "#unknown_field": null}}"""


def call_claude(profile_keys: list, fields: list) -> dict:
    """Call Claude API to match fields to profile keys."""
    if not API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    prompt = build_prompt(profile_keys, fields)

    request_body = {
        "model": "claude-haiku-4-5",
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01"
    }

    req = Request(
        ANTHROPIC_API_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    print(f"[Claude API] Sending {len(fields)} fields to match...")

    try:
        with urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"[Claude API] Response received")

        # Extract the text content from Claude's response
        content = result.get("content", [])
        if not content or content[0].get("type") != "text":
            raise ValueError("Unexpected response format from Claude")

        text = content[0].get("text", "")

        # Parse the JSON response
        # Handle potential markdown code blocks
        text = text.strip()
        if text.startswith("```"):
            # Remove markdown code block
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            text = text.strip()

        mapping = json.loads(text)
        matched = sum(1 for v in mapping.values() if v is not None)
        print(f"[Claude API] Matched {matched}/{len(mapping)} fields")
        return mapping

    except HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise ValueError(f"Claude API error {e.code}: {error_body}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Claude response as JSON: {e}")


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the proxy server."""

    def _send_response(self, status: int, data: dict):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self._send_response(200, {"status": "ok", "api_key_set": bool(API_KEY)})
        else:
            self._send_response(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests."""
        if self.path == "/match-fields":
            try:
                # Read request body
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)

                profile_keys = data.get("profile_keys", [])
                fields = data.get("fields", [])

                if not fields:
                    self._send_response(400, {"error": "No fields provided"})
                    return

                # Call Claude API
                mapping = call_claude(profile_keys, fields)
                self._send_response(200, {"mapping": mapping})

            except ValueError as e:
                self._send_response(500, {"error": str(e)})
            except json.JSONDecodeError:
                self._send_response(400, {"error": "Invalid JSON in request body"})
            except Exception as e:
                self._send_response(500, {"error": f"Internal error: {str(e)}"})
        else:
            self._send_response(404, {"error": "Not found"})

    def log_message(self, format, *args):
        """Log HTTP requests."""
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    """Start the server."""
    if not API_KEY:
        print("WARNING: ANTHROPIC_API_KEY environment variable not set!")
        print("Set it with: export ANTHROPIC_API_KEY=sk-...")
        print()

    server = HTTPServer(("localhost", PORT), RequestHandler)
    print(f"LLM Field Matcher server running on http://localhost:{PORT}")
    print("Endpoints:")
    print(f"  GET  http://localhost:{PORT}/health")
    print(f"  POST http://localhost:{PORT}/match-fields")
    print()
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
