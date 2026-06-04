# QB Solver - Question Bank Answer Generator

Upload any question bank file and get a clean, detailed PDF answer sheet.
Powered by Groq and Llama 3.3.

## Supported Input Formats
- PDF (.pdf)
- Word Document (.docx)
- Excel (.xlsx)
- Plain Text (.txt)

## Setup

### Step 1 - Install Python
Download Python 3.10+ from https://python.org.
On Windows, check "Add Python to PATH" during install.

### Step 2 - Install Dependencies
Open Terminal or Command Prompt in this folder and run:

    pip install -r requirements.txt

### Step 3 - Set Your Groq API Key
Get a Groq API key. You can either paste it when the program asks, or set it before running the solver.

Windows PowerShell:

    $env:GROQ_API_KEY="your_api_key_here"

Mac/Linux:

    export GROQ_API_KEY="your_api_key_here"

## How To Use

### Option A - Command Line
    python qb_solver.py your_questions.pdf
    python qb_solver.py questions.docx
    python qb_solver.py qb.txt

### Option B - Windows
Double-click run.bat, then drag your file onto the window.

### Option C - Mac/Linux
    bash run.sh your_file.pdf

## Output
The answer PDF is saved in the same folder as your input file.
Example: questions.pdf -> questions_ANSWERS.pdf

## Tips
- Your question bank should have clearly numbered questions (1. 2. 3. ...).
- Works best with 5-30 questions per file.
- For very large question banks, split them into smaller files.
- PDF files with scanned images may not extract text well.

## Troubleshooting
- "ModuleNotFoundError" -> run: pip install -r requirements.txt
- "Groq API key is required" -> paste your API key when prompted or set GROQ_API_KEY first
- "403 Forbidden" -> check your API key and internet connection
- "No questions found" -> make sure questions are numbered in your file
