"""QualiSphere Customer Complaint QMS API.

AI recommendations are decision support only. Complaint disposition, CAPA,
closure, and regulatory reporting remain controlled QA activities.
"""
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Generator, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from sqlalchemy import Date, DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from typing_extensions import TypedDict

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./qualisphere.db")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
).split(",")

engine_options = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class ComplaintRecord(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(100))
    customer: Mapped[str] = mapped_column(String(255))
    product: Mapped[str] = mapped_column(String(255))
    strength: Mapped[str] = mapped_column(String(100), default="")
    batch: Mapped[str] = mapped_column(String(100), index=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    complaint_type: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(32), default="Medium")
    priority: Mapped[str] = mapped_column(String(32), default="Standard")
    status: Mapped[str] = mapped_column(String(64), default="Under QA Review")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ComplaintCreate(BaseModel):
    source: str = ""
    customer: str = ""
    product: str = ""
    strength: str = ""
    batch: str = ""
    expiry_date: Optional[date] = None
    quantity: Optional[float] = None
    complaint_type: str = ""
    description: str = Field(min_length=5, max_length=10000)
    severity: str = "Medium"
    priority: str = "Standard"


class Analysis(BaseModel):
    completeness: int
    risk: str
    duplicate_probability: int
    summary: str
    root_cause_recommendation: str
    capa_recommendation: str
    disclaimer: str = "Decision support only; QA approval and investigation remain required."


class ComplaintState(TypedDict):
    complaint: ComplaintCreate
    analysis: Analysis


def rule_analysis(complaint: ComplaintCreate) -> Analysis:
    """Safe demo fallback. Replace this node with Groq structured output in production."""
    text = f"{complaint.complaint_type} {complaint.description}".lower()
    high_risk = any(term in text for term in ("broken", "crack", "contamin", "patient", "adverse", "foreign"))
    required = [complaint.source, complaint.customer, complaint.product, complaint.batch, complaint.complaint_type, complaint.description]
    return Analysis(
        completeness=round(100 * sum(bool(item) for item in required) / len(required)),
        risk="High" if high_risk else "Medium",
        duplicate_probability=82 if "broken" in text or "crack" in text else 21,
        summary=(f"{complaint.customer or 'Customer'} reported {complaint.complaint_type or 'a product-quality concern'} "
                 f"for {complaint.product or 'the product'} batch {complaint.batch or 'not provided'}."),
        root_cause_recommendation="Assess compression, material handling and packaging-line controls; compare retain samples and batch records.",
        capa_recommendation="Open a risk-based investigation, trend related lots, and define corrective actions with effectiveness checks if the issue is confirmed.",
    )


def quality_assessment(state: ComplaintState):
    return {"analysis": rule_analysis(state["complaint"])}


workflow = StateGraph(ComplaintState)
workflow.add_node("quality_assessment", quality_assessment)
workflow.add_edge(START, "quality_assessment")
workflow.add_edge("quality_assessment", END)
complaint_graph = workflow.compile()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="QualiSphere Complaint QMS", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "qualisphere-api"}


@app.post("/api/complaints/analyze", response_model=Analysis)
async def analyze_complaint(complaint: ComplaintCreate):
    return complaint_graph.invoke({"complaint": complaint})["analysis"]


@app.post("/api/complaints", status_code=201)
async def create_complaint(complaint: ComplaintCreate, db: Session = Depends(get_db)):
    year = datetime.utcnow().year
    sequence = db.scalar(select(ComplaintRecord.id).where(ComplaintRecord.complaint_number.like(f"CC-{year}-%")).order_by(ComplaintRecord.id.desc())) or 0
    complaint_number = f"CC-{year}-{sequence + 1:04d}"
    record = ComplaintRecord(complaint_number=complaint_number, **complaint.model_dump())
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Complaint record could not be persisted.") from exc
    return {"id": record.complaint_number, "status": record.status, "created_at": record.created_at, "complaint": complaint}
