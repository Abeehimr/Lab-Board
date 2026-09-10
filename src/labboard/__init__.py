def main() -> None:
    import uvicorn

    uvicorn.run("labboard.app:app", host="0.0.0.0", port=8000)


__all__ = ["main"]
