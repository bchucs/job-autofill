# Job Application Auto-Fill Chrome Extension

A Chrome extension that automatically fills job application forms with your saved profile.

## Installation

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select this `extension` folder

## Setup

1. Click the extension icon in your toolbar
2. Click the gear icon to open Settings
3. Fill in your profile information
4. Click "Save Profile"

**Or import from existing config:**
1. Run `python3 import_profile.py` to convert your config.yaml
2. In extension settings, click "Import Profile"
3. Select the generated `profile.json`

## Usage

1. Navigate to any job application page
2. Click the extension icon
3. Review the detected fields
4. Click "Fill Form"
5. Review and submit manually

## Features

- Detects common ATS platforms (Greenhouse, Lever, Workday, etc.)
- Auto-fills personal info, education, work authorization
- Handles EEOC/demographic questions
- Shows what will be filled before filling
- Works on any job application form

## Supported Fields

- Name, email, phone
- Address (street, city, state, zip, country)
- LinkedIn, GitHub, portfolio URLs
- Education (school, degree, major, GPA, dates)
- High school info
- Test scores (SAT, ACT)
- Work authorization & sponsorship
- EEOC demographics (gender, race, veteran, disability)
- Application questions (applied before, other offers)

## File Uploads

The extension detects resume/cover letter upload fields but cannot auto-upload files (browser security restriction). You'll need to upload these manually.

## Privacy

All data is stored locally in Chrome's sync storage. No data is sent to any server.
