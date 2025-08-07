from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import aiohttp

app = FastAPI()

@app.get("/stream")
async def stream(request: Request):
    rd_url = request.query_params.get("link")
    if not rd_url or not rd_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Missing or invalid 'link' parameter")

    headers = {}
    if range_header := request.headers.get("Range"):
        headers["Range"] = range_header
        print(f"📡 Cliente solicitó rango: {range_header}")

    print(f"🔗 Enlace solicitado: {rd_url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(rd_url, headers=headers, timeout=aiohttp.ClientTimeout(total=None)) as rd_resp:
                # Si Content-Range está presente, mantenlo. Pero no pongas Content-Length.
                response_headers = {}
                
                if "Content-Type" in rd_resp.headers:
                    response_headers["Content-Type"] = rd_resp.headers["Content-Type"]
                if "Content-Range" in rd_resp.headers:
                    response_headers["Content-Range"] = rd_resp.headers["Content-Range"]
                if "Accept-Ranges" in rd_resp.headers:
                    response_headers["Accept-Ranges"] = rd_resp.headers["Accept-Ranges"]
                if "ETag" in rd_resp.headers:
                    response_headers["ETag"] = rd_resp.headers["ETag"]
                if "Last-Modified" in rd_resp.headers:
                    response_headers["Last-Modified"] = rd_resp.headers["Last-Modified"]

                response_headers.setdefault("Accept-Ranges", "bytes")

                status_code = 206 if "Content-Range" in rd_resp.headers else 200

                async def content_stream():
                    try:
                        async for chunk in rd_resp.content.iter_chunked(4 * 1024 * 1024):
                            yield chunk
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
