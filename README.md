# IITKQC - IIT Kanpur Confessions Instagram Automation

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/iitkq.c/)

An automated pipeline for processing, moderating, and posting confessions to the IIT Kanpur Confessions Instagram page.

## Overview

This project automates the process of:
1. Fetching confessions from Google Sheets
2. Moderating content using Google's Gemini AI
3. Generating creative captions and summaries
4. Scheduling posts to Instagram using the Graph API

## Features

- 🔄 Automated confession processing pipeline
- 🤖 AI-powered content moderation using Gemini
- 📝 Smart caption generation
- 📅 Automated Instagram post scheduling
- ✅ Duplicate prevention system
- 📊 Google Sheets integration for confession management

Note: Detailed documentation can be found at: [documentation](Documentation.md).

## Tech Stack

- Python 3.x
- Google Sheets API
- Instagram Graph API
- Google Gemini AI
- GitHub Actions (for automation)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/iitkqc/page-automation.git
cd page-automation
```

2. Install dependencies:
```bash
uv sync --frozen
```

3. Set up environment variables:
```bash
GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"
GOOGLE_SHEET_URL="YOUR_GOOGLE_FORMS_ID"
GOOGLE_SHEETS_CREDENTIALS_FILE="google_sheet_credentials_file_base64_encoded"
INSTAGRAM_PAGE_ID="YOUR_INSTAGRAM_PAGE_ID"
INSTAGRAM_APP_ID="YOUR_INSTAGRAM_APP_ID"
INSTAGRAM_APP_SECRET="YOUR_INSTAGRAM_APP_SECRET"
CLOUDINARY_CLOUD_NAME="YOUR_CLOUDINARY_CLOUD_NAME"
CLOUDINARY_API_KEY="YOUR_CLOUDINARY_API_KEY"
CLOUDINARY_API_SECRET="YOUR_CLOUDINARY_API_SECRET"
MAX_CONFESSION_PER_RUN=8
```

## Google form response sheet header should look like

| Timestamp | Your Confession |	Status	| {{Confession count}} | {{INSTAGRAM_ACCESS_TOKEN}} |
|-----------|-----------------|---------|----------------------|----------------------------|

## File Structure
```
src/
├── gemini_processor.py      # GeminiProcessor class
├── google_form_reader.py    # GoogleFormReader class
├── insta_poster.py         # InstagramPoster + ConfessionImageGenerator classes
└── main.py                 # ConfessionAutomation orchestrator class
```

## Contributing

We welcome contributions to improve the project! Here are some areas where you can help:

1. Enhance the AI moderation system
2. Improve caption generation
3. Add new features to the automation pipeline
4. Optimize the posting schedule
5. Add better error handling and logging
6. Improve the documentation

To contribute:
1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Contact

For any questions or suggestions, please reach out through:
- Instagram: [@iitkq.c](https://www.instagram.com/iitkq.c/)
- GitHub Issues

## Acknowledgments

- Thanks to all contributors who help maintain and improve this project