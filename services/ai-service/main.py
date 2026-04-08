from fastapi import FastAPI

app = FastAPI(
    title="SmartBiz AI Service",
    root_path="/ai")


@app.get("/")
def health():
    return {"status": "AI service running"}

@app.get("/ping")
def ping():
    return {"message": "AI service alive"}