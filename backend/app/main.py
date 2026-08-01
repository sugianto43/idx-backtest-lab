from fastapi import FastAPI

app = FastAPI(title="idx-backtesting-lab-api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
