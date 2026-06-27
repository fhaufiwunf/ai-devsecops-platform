import os
import json
from datetime import datetime

import requests
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker


app = FastAPI(title="DevSecOps AI Dashboard")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/devsecops_scans.db")
if DATABASE_URL.startswith("sqlite:///"):
    db_file = DATABASE_URL.replace("sqlite:///", "", 1)
    db_dir = os.path.dirname(db_file)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"))
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def normalize_severity(value: str) -> str:
    s = str(value or "").strip().lower()

    if s in {"error", "high"} or "high" in s:
        return "high"
    if s in {"critical"} or "critical" in s:
        return "critical"
    if s in {"warning", "medium", "moderate"} or "medium" in s or "moderate" in s:
        return "medium"
    if s == "low" or "low" in s:
        return "low"
    if s in {"info", "informational"} or "info" in s:
        return "info"

    return "info"


def top_severity_from_counts(counts: dict) -> str:
    for sev in ["critical", "high", "medium", "low", "info"]:
        if int(counts.get(sev, 0) or 0) > 0:
            return sev
    return "info"


def calculate_counts(findings: list[dict]) -> dict:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for finding in findings:
        sev = normalize_severity(finding.get("severity") or finding.get("raw_severity"))
        counts[sev] += 1
    return counts


def get_source_context(file_path: str, line_number, radius: int = 5) -> str:
    if not file_path:
        return ""

    try:
        line_number = int(line_number)
    except Exception:
        return ""

    if str(file_path).startswith(("http://", "https://")):
        return ""

    safe_path = str(file_path).lstrip("/")
    full_path = os.path.abspath(os.path.join(SOURCE_ROOT, safe_path))
    source_root_abs = os.path.abspath(SOURCE_ROOT)

    try:
        if os.path.commonpath([full_path, source_root_abs]) != source_root_abs:
            return "Blocked unsafe file path."
    except ValueError:
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


@app.post("/api/scans")
async def save_scan(payload: dict):
    db = SessionLocal()

    try:
        ai_items = payload.get("ai_analyzed_findings") or payload.get("ai_findings") or []
        normal_items = payload.get("normal_findings_report") or payload.get("normal_findings") or []
        all_items = payload.get("all_findings") or (ai_items + normal_items)

        severity_counts = payload.get("severity_counts") or calculate_counts(all_items)
        top_severity = payload.get("severity") or top_severity_from_counts(severity_counts)

        max_item_risk = max([float(f.get("risk_score", 0) or 0) for f in all_items] or [0])
        risk_score = float(
            payload.get("risk_score")
            or payload.get("pre_risk_score")
            or max_item_risk
            or 0
        )

        has_blocking_issue = bool(payload.get("should_block_pipeline")) or any(
            normalize_severity(f.get("severity") or f.get("raw_severity")) in {"critical", "high"}
            or float(f.get("risk_score", 0) or 0) >= 8
            for f in all_items
        )

        decision = str(payload.get("pipeline_decision") or "ALLOW").upper()
        if has_blocking_issue:
            decision = "BLOCK"
        elif decision not in {"ALLOW", "BLOCK"}:
            decision = "BLOCK"

        ai_summary = payload.get("ai_summary") or ""
        ai_fix = payload.get("ai_fix_suggestion") or ""
        if ai_items:
            ai_summary = ai_summary or ai_items[0].get("ai_summary", "")
            ai_fix = ai_fix or ai_items[0].get("ai_fix_suggestion", "")

        scan = Scan(
            report_type=payload.get("report_type", "DevSecOps Security Report"),
            total_findings=int(payload.get("total_findings") or len(all_items)),
            pipeline_decision=decision,
            risk_score=risk_score,
            severity=top_severity,
            ai_summary=ai_summary,
            ai_fix_suggestion=ai_fix,
            raw_json=json.dumps(payload, ensure_ascii=False),
        )

        db.add(scan)
        db.commit()
        db.refresh(scan)
        scan_id = scan.id

        for f in all_items:
            finding = Finding(
                scan_id=scan_id,
                tool=f.get("tool", ""),
                type=f.get("type", ""),
                severity=normalize_severity(f.get("severity") or f.get("raw_severity")),
                title=f.get("title", ""),
                file_or_url=f.get("file") or f.get("file_or_url") or f.get("url") or "",
                line=str(f.get("line", "-")),
                suggested_fix=(
                    f.get("ai_fix_suggestion")
                    or f.get("suggested_fix")
                    or f.get("solution")
                    or f.get("fixed_version")
                    or ""
                ),
                raw_json=json.dumps(f, ensure_ascii=False),
            )
            db.add(finding)

        db.commit()

        return {
            "status": "saved",
            "scan_id": scan_id,
            "pipeline_decision": decision,
            "risk_score": risk_score,
            "severity": top_severity,
        }
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    db = SessionLocal()
    try:
        scans = db.query(Scan).order_by(Scan.created_at.desc()).all()
        findings = db.query(Finding).all()

        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for finding in findings:
            counts[normalize_severity(finding.severity)] += 1

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "scans": scans,
                "critical": counts["critical"],
                "high": counts["high"],
                "medium": counts["medium"],
                "low": counts["low"],
            },
        )
    finally:
        db.close()


@app.get("/scans/{scan_id}", response_class=HTMLResponse)
def scan_detail(request: Request, scan_id: int):
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()
        return templates.TemplateResponse(
            request=request,
            name="scan_detail.html",
            context={"scan": scan, "findings": findings},
        )
    finally:
        db.close()


@app.get("/findings/{finding_id}/chat", response_class=HTMLResponse)
def chat_page(request: Request, finding_id: int):
    db = SessionLocal()
    try:
        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")

        history = (
            db.query(ChatHistory)
            .filter(ChatHistory.finding_id == finding_id)
            .order_by(ChatHistory.created_at.asc())
            .all()
        )

        source_context = get_source_context(finding.file_or_url, finding.line, radius=5)

        return templates.TemplateResponse(
            request=request,
            name="chat.html",
            context={
                "finding": finding,
                "scan_id": finding.scan_id,
                "history": history,
                "answer": None,
                "source_context": source_context,
            },
        )
    finally:
        db.close()


@app.post("/findings/{finding_id}/chat", response_class=HTMLResponse)
def ask_ai(request: Request, finding_id: int, question: str = Form(...)):
    db = SessionLocal()
    try:
        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")

        source_context = get_source_context(finding.file_or_url, finding.line, radius=5)

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
                "suggested_fix": finding.suggested_fix,
            },
            "source_context": source_context,
        }

        try:
            res = requests.post(
            os.getenv("N8N_CHAT_WEBHOOK_URL", "http://n8n:5678/webhook/ai-chat"),
            json=payload,
            timeout=(
                   10,
                   int(os.getenv("AI_REQUEST_TIMEOUT", "600"))
            ),
            )

            res.raise_for_status()

            try:
                data = res.json()
            except Exception:
                data = {"answer": res.text}

            if isinstance(data, list) and len(data) > 0:
                answer = data[0].get("answer", "")
            elif isinstance(data, dict):
                answer = data.get("answer", "")
            else:
                answer = str(data)

            if not answer:
                answer = "AI workflow returned an empty answer."

        except Exception as e:
            answer = f"Failed to call AI workflow: {e}"

        chat = ChatHistory(finding_id=finding.id, question=question, answer=answer)
        db.add(chat)
        db.commit()

        history = (
            db.query(ChatHistory)
            .filter(ChatHistory.finding_id == finding_id)
            .order_by(ChatHistory.created_at.asc())
            .all()
        )

        return templates.TemplateResponse(
            request=request,
            name="chat.html",
            context={
                "finding": finding,
                "scan_id": finding.scan_id,
                "history": history,
                "answer": answer,
                "source_context": source_context,
            },
        )
    finally:
        db.close()
