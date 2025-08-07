from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import aiohttp

app = FastAPI()

@app.get("/stream")
async def stream(request: Request):
    rd_url = request.query_params.get("link")
    if not rd_url or not rd_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Missing or invalid 'link' parameter")

    # Forward Range header if present
    headers = {}
    if range_header := request.headers.get("Range"):
        headers["Range"] = range_header
        print(f"📡 Cliente solicitó rango: {range_header}")

    print(f"🔗 Enlace solicitado: {rd_url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request("GET", rd_url, headers=headers, timeout=aiohttp.ClientTimeout(total=None)) as rd_resp:
                # Copy headers
                response_headers = {}
                for key in ["Content-Type", "Content-Length", "Content-Range", "Accept-Ranges", "ETag", "Last-Modified"]:
                    if key in rd_resp.headers:
                        response_headers[key] = rd_resp.headers[key]

                # Asegura que se diga que se pueden hacer requests por rango
                response_headers.setdefault("Accept-Ranges", "bytes")

                # Determina status
                status_code = 206 if "Content-Range" in rd_resp.headers else 200

                # Stream de chunks asincrónico
                async def content_stream():
                    async for chunk in rd_resp.content.iter_chunked(4 * 1024 * 1024):  # 4MB chunks
                        yield chunk

                return StreamingResponse(
                    content_stream(),
                    status_code=status_code,
                    headers=response_headers
                )

    except Exception as e:
        print(f"❌ Error al hacer proxy: {e}")
        raise HTTPException(status_code=500, detail="Proxy error")
