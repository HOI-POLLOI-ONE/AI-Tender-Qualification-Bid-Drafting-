# ── Analyze Tender (Simple Demo Endpoint for Frontend) ─────────

from fastapi import FastAPI, UploadFile, File

app = FastAPI()

@app.post("/analyze", tags=["Demo"])
async def analyze(file: UploadFile = File(...)):
    content = await file.read()

    # TODO: Connect real AI logic here
    # For now returning mock response for dashboard

    return {
        "success": True,
        "score": 82,
        "requirements": [
            "Turnover above ₹5 Cr",
            "EMD Required: ₹2,00,000",
            "3 similar projects needed"
        ]
    }
