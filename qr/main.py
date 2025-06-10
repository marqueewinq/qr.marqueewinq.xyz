import qrcode
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import io
from typing import Optional
from pathlib import Path
import os

from .code import generate_qr_code as _generate_qr_code
from .cache import redis_cache

app = FastAPI(
    title="QR Code Generator API",
    description="A simple API for generating QR codes",
    version="1.0.0",
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@redis_cache(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=os.getenv("REDIS_PORT", 6379),
    serializer=lambda x: json.dumps(x, sort_keys=True),
)
async def generate_qr_code(
    data: str, size: int, border: int, fill_color: str, back_color: str
) -> io.BytesIO:
    """Wrapper around the actual QR code generator to cache the result."""
    qr_image = await _generate_qr_code(data, size, border, fill_color, back_color)
    image_stream = io.BytesIO()
    qr_image.save(image_stream, format="PNG")
    image_stream.seek(0)
    return image_stream


class QRCodeRequest(BaseModel):
    data: str
    size: Optional[int] = 10
    border: Optional[int] = 4
    fill_color: Optional[str] = "black"
    back_color: Optional[str] = "white"


@app.head("/")
async def head():
    return Response(status_code=200)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post(
    "/generate",
    response_class=StreamingResponse,
    response_description="QR code image",
    responses={
        200: {
            "description": "QR code image",
            "content": {"image/png": {}},
        },
        409: {
            "description": "Invalid request",
            "content": {"application/json": {"example": {"detail": "Invalid request"}}},
        },
    },
)
async def generate(request: QRCodeRequest) -> StreamingResponse:
    try:
        image_stream = await generate_qr_code(
            request.data,
            request.size,
            request.border,
            request.fill_color,
            request.back_color,
        )
        return StreamingResponse(image_stream, media_type="image/png")
    except (ValueError, qrcode.exceptions.DataOverflowError) as e:
        raise HTTPException(status_code=409, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
