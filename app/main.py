from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict

# --------------------
# Guardrail configuration
# --------------------
MAX_PROMPT_LENGTH = 500
MAX_ESTIMATED_COST_USD = 0.02
BANNED_WORDS = ["password", "ssn", "credit card"]

# --------------------
# In-memory audit log
# --------------------
AUDIT_LOGS: List[Dict] = []

app = FastAPI(title="AI Platform")

# --------------------
# Request / Response Models
# --------------------
class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str


# --------------------
# Helper functions
# --------------------
def estimate_cost(prompt: str) -> float:
    # Rough estimate: 1 token ≈ 4 characters
    tokens = max(1, len(prompt) // 4)
    return (tokens / 1000) * 0.002


def validate_prompt(prompt: str):
    if len(prompt) > MAX_PROMPT_LENGTH:
        return False, "Prompt too long"

    lowered = prompt.lower()
    for word in BANNED_WORDS:
        if word in lowered:
            return False, f"Blocked due to unsafe word: {word}"

    estimated_cost = estimate_cost(prompt)
    if estimated_cost > MAX_ESTIMATED_COST_USD:
        return False, f"Estimated cost ${estimated_cost:.4f} exceeds limit"

    return True, None


def log_decision(prompt: str, blocked: bool, reason: str, cost: float):
    AUDIT_LOGS.append({
        "timestamp": datetime.utcnow().isoformat(),
        "prompt_preview": prompt[:100],
        "blocked": blocked,
        "reason": reason,
        "estimated_cost_usd": round(cost, 4)
    })


# --------------------
# API Endpoints
# --------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ai-platform",
        "message": "AI Platform is running"
    }


@app.post("/ai/chat")
def chat(req: ChatRequest):
    allowed, reason = validate_prompt(req.prompt)
    estimated_cost = estimate_cost(req.prompt)

    if not allowed:
        log_decision(
            prompt=req.prompt,
            blocked=True,
            reason=reason,
            cost=estimated_cost
        )
        return {
            "blocked": True,
            "reason": reason
        }

    reply = (
        f"🤖 AI Response: Received your prompt.\n"
        f"Estimated cost: ${estimated_cost:.4f}"
    )

    log_decision(
        prompt=req.prompt,
        blocked=False,
        reason="Allowed",
        cost=estimated_cost
    )

    return {
        "blocked": False,
        "response": reply,
        "estimated_cost_usd": estimated_cost
    }


@app.get("/ai/audit-logs")
def get_audit_logs():
    return {
        "total_requests": len(AUDIT_LOGS),
        "logs": AUDIT_LOGS
    }

