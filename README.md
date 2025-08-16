# Competitor Research Crew

A multi-agent AI system for automated competitor research, powered by [CrewAI](https://github.com/joaomdmoura/crewai), Gemini (Google Generative AI), and custom tools for web crawling and news aggregation.

## Features

- **Website Intelligence Scraper:** Extracts product, service, and feature information from a competitor’s website.
- **Competitive Intelligence Researcher:** Gathers recent news, press releases, and blog articles about a company using Serper.dev.
- **Competitive Analysis Strategist:** Summarizes findings into a structured report.

## Project Structure

```
my_first_crew/
├── knowledge/
├── output/
├── src/
│   └── my_first_crew/
│       ├── config/
│       │   ├── agents.yaml
│       │   └── tasks.yaml
│       ├── tools/
│       │   └── custom_tool.py
│       ├── crew.py
│       └── main.py
├── .env
├── pyproject.toml
└── README.md
```

## Setup

### 1. Clone the repository

```sh
git clone <your-repo-url>
cd my_first_crew
```

### 2. Create and activate a virtual environment

```sh
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate
```

### 3. Install dependencies

With uv (recommended):

```sh
uv sync
```

Or with pip:

```sh
pip install -e .
```

### 4. Environment Variables

Create a `.env` file in the root directory with the following content:

```
MODEL=gemini/gemini-2.0-flash-001
GOOGLE_API_KEY=your_google_gemini_api_key
SERPER_API_KEY=your_serper_dev_api_key
```

- Get your [Gemini API key](https://ai.google.dev/gemini-api/docs/get-api-key).
- Get your [Serper.dev API key](https://serper.dev/).

### 5. Configure Agents and Tasks

Edit `src/my_first_crew/config/agents.yaml` and `src/my_first_crew/config/tasks.yaml` to customize agent roles, goals, and task descriptions.

## Usage

Run the main script to analyze a list of companies:

```sh
python -m my_first_crew.main
```

Or via the CLI entrypoint after install:

```sh
my_first_crew
```

Results and reports will be saved in the `output/` directory.

## Custom Tools

- **Website Crawler Tool:** Extracts text from a competitor’s website.
- **News Search Tool:** Fetches recent news using SerpAPI.

You can extend or modify these tools in `src/my_first_crew/tools/custom_tool.py`.

## Playwright (for crawling)

This project uses Playwright to render websites. Install browsers once:

```sh
python -m playwright install --with-deps
```

On Windows PowerShell, you may omit --with-deps.

## Troubleshooting

- **Quota/Rate Limit Errors:** If you see HTTP 429 errors, you have exceeded your Gemini or SerpAPI quota. Wait and retry, or upgrade your plan.
- **Empty or None LLM Responses:** Ensure your API keys are set and valid. Check your `.env` file.
- **No News Results:** Make sure your SerpAPI key is correct and you have quota left.

## License

MIT License
