
## 1. AI DevSecOps Platform

AI-powered DevSecOps orchestration platform using:

- OWASP ZAP
- Semgrep
- Trivy
- n8n
- Ollama LLM
- FastAPI Dashboard

This platform automates security scanning, AI-based risk analysis, vulnerability reporting, and scan history management through a unified workflow.

Thêm screenshot dashboard ngay đầu.

## 2. Architecture Diagram

Bạn nên thêm ảnh:

GitHub Actions
  ↓
Trivy / Semgrep / ZAP
  ↓
n8n Workflow
  ↓
Ollama AI Analysis
  ↓
FastAPI Dashboard + SQLite

Ví dụ:

## 3. Architecture

![Architecture](docs/images/architecture.png)


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

## 5. Tech Stack

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
5. Quick Start (QUAN TRỌNG NHẤT)

Đây là phần người dùng nhìn đầu tiên.

## 6. Quick Start

1. Clone repository

```bash
git clone https://github.com/yourname/ai-devsecops-platform.git
cd ai-devsecops-platform
Configure environment
cp .env.example .env

Edit .env:

PUBLIC_N8N_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app/webhook/security-scan
SOURCE_CODE_PATH=/path/to/source/code
OLLAMA_BASE_URL=http://172.17.0.1:11434
Run platform
docker compose up -d --build
Access services
Service	URL
Dashboard	http://localhost:8000
n8n	http://localhost:5678
```
---

2. Setup Ollama

```md
# Setup Ollama

Install Ollama:

https://ollama.com/download

Pull model:

```bash
ollama pull qwen2.5:3b

Verify:

curl http://localhost:11434/api/tags
```
---

3. Import n8n Workflow

```md
# Import Workflow

1. Open n8n
2. Import workflow JSON from:

import two flow in /n8n/workflow
```
---

4. GitHub Actions Integration

```md
# GitHub Actions Integration

Configure repository secret:

```text
N8N_WEBHOOK_URL

Example:

env:
  N8N_WEBHOOK_URL: https://xxxxx.ngrok-free.dev/webhook/security-scan
```
---

## 7. Screenshots

Bạn nên có:
![Architecture](docs/images/architecture.png)
```text
Dashboard
n8n workflow
AI findings
GitHub Actions pipeline

Ví dụ:

## Dashboard

![Dashboard](docs/images/dashboard.png)
```
## 8. n8n Workflow

![Workflow](docs/images/workflow.png)

## 9. Project Structure
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
---

## 10. Troubleshooting

Ví dụ:

```md
# Troubleshooting

## n8n cannot connect to Ollama

Change:

```env
OLLAMA_BASE_URL=http://172.17.0.1:11434
Port already allocated

Change:

N8N_PORT=5679
```
---

## 11. Future Improvements

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
## 12. License
License
MIT License
