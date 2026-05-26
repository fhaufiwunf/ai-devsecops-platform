## 1. Hero section
AI DevSecOps Platform

AI-powered DevSecOps orchestration platform using:

- OWASP ZAP
- Semgrep
- Trivy
- n8n
- Ollama LLM
- FastAPI Dashboard

This platform automates security scanning, AI-based risk analysis, vulnerability reporting, and scan history management through a unified workflow.
## 2. Architecture
GitHub Actions
  ↓
Trivy / Semgrep / ZAP
  ↓
n8n Workflow
  ↓
Ollama AI Analysis
  ↓
FastAPI Dashboard + SQLite
## 3. Workflow

## 4. Features

- Automated CI/CD security scanning
- AI-powered vulnerability analysis
- Centralized dashboard
- Scan history database
- AI remediation suggestions
- Risk scoring
- Pipeline blocking decision
- Dockerized deployment
- Source code mounting support
- Open-source extensible architecture
## 5. Tech stack

| Component | Technology |
|---|---|
| Workflow Automation | n8n |
| AI Engine | Ollama |
| SAST | Semgrep |
| Dependency Scan | Trivy |
| DAST | OWASP ZAP |
| Dashboard | FastAPI |
| Database | SQLite |
| Containerization | Docker |
| CI/CD | GitHub Actions |

## 6. Quick start
Quick Start
Clone repository

```bash
git clone https://github.com/yourname/ai-devsecops-platform.git
cd ai-devsecops-platform
```
Configure environment
```
cp .env.example .env
```
Edit .env:

```bash
PUBLIC_N8N_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app/webhook/security-scan
SOURCE_CODE_PATH=/path/to/source/code
OLLAMA_BASE_URL=http://172.17.0.1:11434
```
Run platform

```bash
docker compose up -d --build
```
Access services
Service	URL
Dashboard	http://localhost:8000
n8n	http://localhost:5679

---

6.1 Setup Ollama

```md
# Setup Ollama

Install Ollama:

https://ollama.com/download

Pull model:

ollama pull qwen2.5:3b
```

Verify:
```
curl http://localhost:11434/api/tags
```

---

6.2 Import n8n Workflow

```md
# Import Workflow

1. Open n8n
2. Import workflow JSON from:

```text
n8n/workflows/
```

---

6.3 GitHub Actions Integration

```md
# GitHub Actions Integration

Configure repository secret:

```text
N8N_WEBHOOK_URL
```

## 7. Screenshots
```text
Dashboard
n8n workflow
AI findings
GitHub Actions pipeline
```

## 8.Project Structure
Project Structure

```text
ai-devsecops-platform/
├── dashboard/
├── n8n/
├── github-actions/
├── docs/
├── scripts/
├── sample-reports/
├── docker-compose.yml
└── README.md
```
## 9. Troubleshooting
```md
# Troubleshooting

## n8n cannot connect to Ollama

Change:
```env
OLLAMA_BASE_URL=http://172.17.0.1:11434
```
## 10. Future Improvements
```md
# Future Improvements

- PostgreSQL support
- Multi-user authentication
- PDF export
- Kubernetes deployment
- AI code auto-remediation
- Slack/Discord integration
- CVE correlation engine
```

## 11.License
License

MIT License
