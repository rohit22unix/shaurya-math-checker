# Math Worksheet Checker (Starter)

This is a beginner-friendly Streamlit app for checking math worksheet answers.

## What it can do

- Supports MCQ-style worksheet questions.
- Mobile-friendly worksheet image intake:
  - Open camera directly and capture worksheet photo.
  - Upload worksheet image from gallery/files.
- OCR extraction from worksheet photos.
- Automatic MCQ parsing: detects question text and options from scanned worksheet.
- Marks each answer as:
  - Correct
  - Incorrect
  - Unattempted
  - Question issue (excluded from adjusted score)
- Handles the special case where student answer is not in worksheet options.
- Shows explanation for incorrect answers.
- Shows both strict and adjusted score.
- Report export:
  - Download CSV report.
  - Download PDF report.

## Run locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the app:

```bash
streamlit run app.py
```

## JSON worksheet format

Use a JSON array of objects:

```json
[
  {
    "qid": "Q1",
    "prompt": "What is 4 + 6?",
    "options": ["8", "9", "10", "11"],
    "correct_answer": "10",
    "explanation": "4 + 6 = 10",
    "points": 1
  }
]
```

## Next upgrades

- Add short-answer checking with tolerance rules.
- Add answer-key OCR or answer-key upload from a separate teacher sheet.
- Improve parser for layouts where options are in columns.

## iPhone quick use

1. Open the Streamlit app in Safari.
2. In Worksheet Photo Upload, choose Open camera.
3. Tap the camera button, capture the worksheet, and upload.
4. If needed, switch to Upload image to pick from Photos.

## Free deploy on Render

You can get a free public HTTPS URL like:

- https://mathchecker.onrender.com

If that exact name is taken, Render will give another close one.

1. Create a GitHub repository and push this project.
2. Go to Render dashboard and click New + then Blueprint.
3. Connect your GitHub repo.
4. Render will read render.yaml automatically.
5. Confirm and deploy.
6. Open your Render app URL on iPhone Safari.

Notes:

- Free Render services may sleep when idle. First open can take some time.
- Camera permission should work because Render provides HTTPS.
