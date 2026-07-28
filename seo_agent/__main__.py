"""Application entry point for running seo_agent directly."""

from seo_agent.api.app import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)