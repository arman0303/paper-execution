import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.pipeline import DatricsText2SQLPipeline
from app.schemas.sql import GeneratedSQLResponse

app = FastAPI(
    title="Datrics Text2SQL API",
    description="Backend service implementing arXiv:2506.12234v1",
    version="1.0.0"
)

pipeline: Optional[DatricsText2SQLPipeline] = None

def get_pipeline() -> DatricsText2SQLPipeline:
    global pipeline
    if pipeline is None:
        pipeline = DatricsText2SQLPipeline()
    return pipeline

class QueryRequest(BaseModel):
    question: str

@app.on_event("startup")
def startup_event():
    get_pipeline()

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "datrics-text2sql"}

@app.post("/api/query", response_model=GeneratedSQLResponse)
def run_query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    p = get_pipeline()
    return p.process_query(request.question)

@app.get("/api/tables")
def get_tables():
    p = get_pipeline()
    return {
        "tables": {name: doc.model_dump() for name, doc in p.indexing_pipeline.table_docs.items()}
    }

@app.get("/api/examples")
def get_examples():
    p = get_pipeline()
    return {
        "examples": [ex.model_dump() for ex in p.indexing_pipeline.train_examples.values()]
    }

@app.post("/api/reindex")
def reindex_kb():
    p = get_pipeline()
    stats = p.indexing_pipeline.index_all()
    return {"status": "success", "stats": stats}
