# SearchKnowtix

**A multi-agent AI research tool built with Python and Streamlit.**

SearchKnowtix is a project I'm building to make researching topics easier. Instead of manually searching through information and putting everything together, the system uses AI agents to help search for relevant information, process it, and turn the findings into a research report.

The goal is simple: make the research process more organized, from the initial search to the final report.

## What it does

- Searches the web for information related to a research topic.
- Uses different AI components to handle parts of the research workflow.
- Processes collected information to help generate a report.
- Provides a Streamlit interface to interact with the system.
- Supports research history where the configured storage is available.

## How it works

The workflow starts when a user enters a research topic. The system searches for relevant information, processes the collected content, and uses its AI workflow to produce a report.

The project is built around separate components for searching, reading, writing, and reviewing research, depending on the workflow configured in the code.

## Built with

- **Python** — core application and research pipeline
- **Streamlit** — web interface
- **LLM APIs** — AI-powered processing and report generation
- **Web search tools** — finding relevant online sources

## Running it locally

### 1. Clone the repository

```bash
git clone https://github.com/lowkeySparkle/SearchKnowtix.git
cd SearchKnowtix
```

### 2. Set up a virtual environment

```bash
python -m venv .venv
```

On Windows, activate it with:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install the dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure your API keys

Add the API keys required by the project to your local environment or supported secrets configuration. Check the existing code to see which providers are being used.

Keep your credentials private. Don't upload your `.env` file or secret keys to GitHub.

### 5. Start the app

```bash
python -m streamlit run app.py
```

Streamlit will print a local URL in the terminal. Open it in your browser to use the application.

## Current status

I'm continuing to work on the project, with a focus on improving the interface, research workflow, and handling of previous research sessions.

Planned improvements include:

- Deploying a public version
- Improving research history
- Making source references easier to review
- Refining error handling and report quality

## License

No license has been added yet.

---

*Built with Python, Streamlit, and AI agents.*
