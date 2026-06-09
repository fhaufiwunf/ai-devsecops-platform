import os
import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import json



app = FastAPI(title="DevSecOps AI Dashboard")

engine = create_engine("sqlite:///./devsecops_scans.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
templates = Jinja2Templates(directory="templates")
SOURCE_ROOT = os.getenv("CONTAINER_SOURCE_PATH", "/workspace/source")

class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String, default="DevSecOps Security Report")
    total_findings = Column(Integer, default=0)
    pipeline_decision = Column(String, default="ALLOW")
    risk_score = Column(Float, default=0)
    severity = Column(String, default="unknown")
    ai_summary = Column(Text, default="")
    ai_fix_suggestion = Column(Text, default="")
    raw_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    tool = Column(String)
    type = Column(String)
    severity = Column(String)
    title = Column(Text)
    file_or_url = Column(Text)
    line = Column(String)
    suggested_fix = Column(Text)
    raw_json = Column(Text)

def get_source_context(file_path: str, line_number, radius: int = 5) -> str:
    if not file_path:
        return ""

    try:
        line_number = int(line_number)
    except Exception:
        return ""

    safe_path = file_path.lstrip("/")

    if safe_path.startswith("http://") or safe_path.startswith("https://"):
        return ""

    full_path = os.path.abspath(os.path.join(SOURCE_ROOT, safe_path))
    source_root_abs = os.path.abspath(SOURCE_ROOT)

    if not full_path.startswith(source_root_abs):
        return "Blocked unsafe file path."

    if not os.path.exists(full_path):
        return f"Source file not found: {full_path}"

    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    start = max(1, line_number - radius)
    end = min(len(lines), line_number + radius)

    context = []
    for i in range(start, end + 1):
        marker = ">>" if i == line_number else "  "
        context.append(f"{marker} {i}: {lines[i - 1].rstrip()}")

    return "\n".join(context)

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"))
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)


@app.post("/api/scans")
async def save_scan(payload: dict):
    db = SessionLocal()

    ai_items = payload.get("ai_analyzed_findings") or payload.get("ai_findings", [])
    normal_items = payload.get("normal_findings_report") or payload.get("normal_findings", [])
    all_items = payload.get("all_findings") or (ai_items + normal_items)

    has_blocking_issue = any(
        str(f.get("severity", "")).upper() == "ERROR"
        or str(f.get("severity", "")).upper() == "CRITICAL"
        or f.get("risk_score", 0) >= 8
        for f in all_items
    )

    decision = payload.get("pipeline_decision", "ALLOW")
    if has_blocking_issue:
        decision = "BLOCK"

    risk_score = 0
    if ai_items:
        risk_score = ai_items[0].get("risk_score", 0)

    ai_summary = ""
    ai_fix = ""
    if ai_items:
        ai_summary = ai_items[0].get("ai_summary", "")
        ai_fix = ai_items[0].get("ai_fix_suggestion", "")

    scan = Scan(
        report_type=payload.get("report_type", "DevSecOps Security Report"),
        total_findings=payload.get("total_findings", len(all_items)),
        pipeline_decision=decision,
        risk_score=risk_score,
        severity="high" if has_blocking_issue else "low",
        ai_summary=ai_summary,
        ai_fix_suggestion=ai_fix,
        raw_json=json.dumps(payload, ensure_ascii=False)
    )

    db.add(scan)
    db.commit()
    db.refresh(scan)

    for f in all_items:
        finding = Finding(
            scan_id=scan.id,
            tool=f.get("tool", ""),
            type=f.get("type", ""),
            severity=f.get("severity", ""),
            title=f.get("title", ""),
            file_or_url=f.get("file") or f.get("file_or_url") or f.get("url") or "",
            line=str(f.get("line", "-")),
            suggested_fix=f.get("ai_fix_suggestion") or f.get("suggested_fix") or f.get("solution") or f.get("fixed_version") or "",
            raw_json=json.dumps(f, ensure_ascii=False)
        )
        db.add(finding)

    db.commit()

    scan_id = scan.id
    db.close()

    return {
        "status": "saved",
        "scan_id": scan.id,
        "pipeline_decision": decision
    }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    db = SessionLocal()
    scans = db.query(Scan).order_by(Scan.created_at.desc()).all()
    db.close()

    critical = 0
    high = 0
    medium = 0
    low = 0

    for scan in scans:
        sev = (scan.severity or "").lower()

        if sev == "critical":
            critical += 1
        elif sev == "high":
            high += 1
        elif sev == "medium":
            medium += 1
        elif sev == "low":
            low += 1

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "scans": scans,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low
        }
    )


@app.get("/scans/{scan_id}", response_class=HTMLResponse)
def scan_detail(request: Request, scan_id: int):
    db = SessionLocal()
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()
    db.close()
    return templates.TemplateResponse(
    	request=request,
    	name="scan_detail.html",
    	context={"scan": scan, "findings": findings}
    )
@app.get("/findings/{finding_id}/chat", response_class=HTMLResponse)
def chat_page(request: Request, finding_id: int):
    db = SessionLocal()
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    history = (
        db.query(ChatHistory)
        .filter(ChatHistory.finding_id == finding_id)
        .order_by(ChatHistory.created_at.asc())
        .all()
    )
    db.close()

    source_context = get_source_context(
        finding.file_or_url,
        finding.line,
        radius=5
    )

    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "finding": finding,
            "scan_id": finding.scan_id,
            "history": history,
            "answer": None,
            "source_context": source_context
        }
    )


@app.post("/findings/{finding_id}/chat", response_class=HTMLResponse)
def ask_ai(request: Request, finding_id: int, question: str = Form(...)):
    db = SessionLocal()
    finding = db.query(Finding).filter(Finding.id == finding_id).first()

    source_context = get_source_context(
        finding.file_or_url,
        finding.line,
        radius=5
    )

    payload = {
        "finding_id": finding.id,
        "question": question,
        "finding": {
            "tool": finding.tool,
            "type": finding.type,
            "severity": finding.severity,
            "title": finding.title,
            "file_or_url": finding.file_or_url,
            "line": finding.line,
            "suggested_fix": finding.suggested_fix
        },
        "source_context": source_context
    }

    try:
        res = requests.post(
            os.getenv("N8N_CHAT_WEBHOOK_URL", "http://n8n:5678/webhook/ai-chat"),
            json=payload,
            timeout=180
        )

        data = res.json()

        if isinstance(data, list) and len(data) > 0:
            answer = data[0].get("answer", "")
        elif isinstance(data, dict):
            answer = data.get("answer", "")
        else:
            answer = str(data)

    except Exception as e:
        answer = f"Failed to call AI workflow: {e}"

    chat = ChatHistory(
        finding_id=finding.id,
        question=question,
        answer=answer
    )
    db.add(chat)
    db.commit()

    history = (
        db.query(ChatHistory)
        .filter(ChatHistory.finding_id == finding_id)
        .order_by(ChatHistory.created_at.asc())
        .all()
    )

    scan_id = finding.scan_id
    db.close()

    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "finding": finding,
            "scan_id": scan_id,
            "history": history,
            "answer": answer
        }
    )
