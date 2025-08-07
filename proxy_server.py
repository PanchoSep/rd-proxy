from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import aiohttp

app = FastAPI()

@app.get("/stream")
async def stream(request: Request):
    rd_url = request.query_params.get("link")
    if not rd_url or not rd_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Missing or invalid 'link' parameter")

    headers = {}
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header
        print(f"📡 Cliente solicitó rango: {range_header}")

    user_agent = request.headers.get("User-Agent", "")
    is_ffprobe = "ffprobe" in user_agent.lower()
    if is_ffprobe:
        print("🎯 Solicitud detectada como ffprobe")

    print(f"🔗 Enlace solicitado: {rd_url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(rd_url, headers=headers, timeout=aiohttp.ClientTimeout(total=None)) as rd_resp:
                response_headers = {
                    k: v for k, v in rd_resp.headers.items()
                    if k.lower() in [
                        "content-type",
                        "content-range",
                        "accept-ranges",
                        "etag",
                        "last-modified"
                    ]
                }

                response_headers.setdefault("Accept-Ranges", "bytes")
                status_code = 206 if "Content-Range" in rd_resp.headers else 200

                async def content_stream():
                    try:
                        read_bytes = 0
                        limit_bytes = 10 * 1024 * 1024  # 10 MB para ffprobe

                        async for chunk in rd_resp.content.iter_chunked(1024 * 1024):  # 1MB chunks
                            read_bytes += len(chunk)
                            yield chunk

                            if is_ffprobe and read_bytes >= limit_bytes:
                                print(f"🛑 Corte anticipado: enviado {read_bytes} bytes para ffprobe")
                                break

                    except aiohttp.ClientConnectionError:
                        print("⚠️ Real-Debrid cerró la conexión antes de tiempo.")

                return StreamingResponse(
                    content_stream(),
                    status_code=status_code,
                    headers=response_headers
                )

    except Exception as e:
        print(f"❌ Error general en el proxy: {e}")
        raise HTTPException(status_code=500, detail="Proxy error")
