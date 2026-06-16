from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import httpx, os, json

app = FastAPI()
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

@app.post("/api/gemini")
async def gemini_proxy(request: Request):
    if not GEMINI_KEY:
        raise HTTPException(500, "GEMINI_KEY not configured")
    body = await request.json()
    last_err = None
    async with httpx.AsyncClient(timeout=30) as client:
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            for attempt in range(2):
                try:
                    r = await client.post(url,
                        headers={"Content-Type":"application/json","x-goog-api-key": GEMINI_KEY},
                        content=json.dumps(body))
                    data = r.json()
                    if r.status_code == 503 or "high demand" in str(data.get("error",{}).get("message","")):
                        if attempt == 0: continue
                        break
                    if not r.is_success:
                        last_err = data.get("error",{}).get("message", f"HTTP {r.status_code}")
                        break
                    text = data.get("candidates",[{}])[0].get("content",{}).get("parts",[{}])[0].get("text","")
                    if text:
                        return JSONResponse({"text": text})
                except Exception as e:
                    last_err = str(e)
    raise HTTPException(502, last_err or "All models failed")

# serve static files (index.html etc.)
app.mount("/", StaticFiles(directory=".", html=True), name="static")
