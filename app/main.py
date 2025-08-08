from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    """Return a simple message indicating the API is running."""
    return {"message": "LEXA API is running"}
