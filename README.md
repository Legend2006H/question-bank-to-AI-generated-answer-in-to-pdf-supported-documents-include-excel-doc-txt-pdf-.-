# QB Solver

QB Solver reads a question bank file and generates a clean PDF answer sheet using Groq AI.

## Features

- Supports PDF, DOCX, XLSX, and TXT question banks
- Detects numbered questions automatically
- Generates exam-ready answers
- Supports short or detailed answer instructions
- Creates a formatted PDF answer key

## Requirements

- Python 3.10 or newer
- A Groq API key

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in this project folder:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Use your own Groq API key. Do not upload your real `.env` file to GitHub.

If you do not add a `.env` file, the program will ask you to enter your Groq API key when it runs.

## Usage

Run the solver with your question bank file:

```bash
python qb_solver.py sample_questions.txt
```

You can also use:

```bash
python qb_solver.py your_questions.pdf
python qb_solver.py your_questions.docx
python qb_solver.py your_questions.xlsx
```

After running, enter an instruction such as:

```text
Engineering OS exam, first 5 questions short answers, remaining detailed answers
```

## Output

The generated PDF is saved in the same folder as the input file.

Example:

```text
sample_questions.txt -> sample_questions_ANSWERS.pdf
```

## Notes

- Questions should be clearly numbered, like `1.`, `2.`, `3.`
- Scanned image PDFs may not extract text correctly
- Generated answer PDFs are ignored by Git
- `.env` is ignored by Git so API keys stay private

## Troubleshooting

- `ModuleNotFoundError`: run `pip install -r requirements.txt`
- `Groq API key is required`: add `GROQ_API_KEY` to `.env` or enter it when prompted
- `Connection error`: check your internet connection and API key
- `No questions found`: make sure your questions are numbered
