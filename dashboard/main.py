from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import json

app = FastAPI(title="DevSecOps AI Dashboard")

engine = create_engine(
    "sqlite:///./data/devsecops_scans.db",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
templates = Jinja2Templates(directory="templates")


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
    return templates.TemplateResponse(
    	request=request,
    	name="index.html",
    	context={"scans": scans}
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
