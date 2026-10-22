# SearchKnowtix
### AI-Powered Multi-Agent Research Platform
**SearchKnowtix** is a Python-based research platform designed to help users explore topics, collect information from web sources, and generate structured research reports using a multi-agent AI workflow.

> From research questions to organized insights — all in one workspace.

---

## ✨ Features

- 🔎 **Web Research** — Search for relevant information on a given topic.
- 💭 **Multi-Agent Architecture** — Organize research tasks across specialized AI components.
- 📚 **Content Processing** — Collect and process information for report generation.
- 📝 **Structured Reports** — Turn research findings into readable outputs.
- 🖥️ **Streamlit Interface** — Access the research workflow through a web-based application.
- 🗂️ **Research History** — Support for retaining and revisiting previous research, depending on the configured storage.

## 🧠 How It Works

1. **Enter a topic** — Provide the subject you want to investigate.
2. **Search the web** — Retrieve potentially relevant online sources.
3. **Process information** — Analyze collected content through the research workflow.
4. **Generate a report** — Produce an organized research output.
5. **Review your findings** — Read the results in the application.

*The exact workflow depends on the agents and features enabled in the current implementation.*

## 🛠️ Technology Stack

- Python
- Streamlit
- Large language model APIs
- Web search and content extraction tools
- Git and GitHub

## 🚀 Getting Started

### Prerequisites

- Python installed on your computer
- API keys for the providers configured in the project
- Git (optional, for cloning the repository)

### 1. Clone the repository

```bash
git clone https://github.com/lowkeySparkle/SearchKnowtix.git
cd SearchKnowtix
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure API keys

Set up the API keys required by your configured providers using environment variables or the appropriate local secrets configuration.

**Never commit API keys, passwords, or private credentials to GitHub.**

### 5. Run the application

```bash
python -m streamlit run app.py
```

Open the local URL printed in your terminal.

## 🔐 Security

- Keep API keys and credentials private.
- Exclude `.env` files and secret configuration files from Git.
- Avoid committing local databases containing personal research history.
- Configure deployment secrets through the hosting platform.

## 🌐 Deployment

SearchKnowtix is intended to run as a Streamlit application. Deployment requires compatible dependencies, valid API credentials, and correct application configuration.

## 🗺️ Roadmap

- [ ] Publish a live demo
- [ ] Improve research-history management
- [ ] Add a visual research pipeline overview
- [ ] Include application screenshots
- [ ] Improve source transparency and error handling

## 🤝 Contributing

Ideas, bug reports, and improvements are welcome. Open an issue to discuss a proposed change before submitting a pull request.

## 📄 License

No license has been selected yet. Licensing terms will be added once the project's distribution and reuse permissions are decided.

---

<p align="center">
  <strong>SearchKnowtix</strong><br>
  <em>Research smarter. Connect the knowledge.</em>
</p>
