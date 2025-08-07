# proxy_server.py
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, PlainTextResponse
import httpx
import uvicorn

app = FastAPI()


@app.get("/stream")
async def stream(request: Request):
    rd_url = request.query_params.get("link")
    if not rd_url or not rd_url.startswith("https://"):
        print("❌ link faltante o inválido")
        return PlainTextResponse("Missing or invalid 'link'", status_code=400)

    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "N/A")
    range_header = request.headers.get("Range")

    print(f"🛰️ User-Agent: {user_agent}")
    print(f"🌐 Cliente: {client_ip} | Método: {request.method}")
    print(f"🔗 Enlace solicitado: {rd_url}")
    print(f"📡 Cliente solicitó rango: {range_header or 'SIN RANGO'}")

    headers = {}
    if range_header:
        headers["Range"] = range_header

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
            rd_response = await client.get(rd_url, headers=headers)

            print(f"✅ Real-Debrid respondió con HTTP {rd_response.status_code}")
            for k, v in rd_response.headers.items():
                print(f"   {k}: {v}")

            content_headers = {
                k: v for k, v in rd_response.headers.items()
                if k.lower() in [
                    "content-type",
                    "content-length",
                    "content-range",
                    "accept-ranges",
                    "cache-control",
                    "etag",
                    "last-modified",
                    "content-disposition"
                ]
            }

            status_code = rd_response.status_code

            async def iter_rd_content():
                try:
                    async for chunk in rd_response.aiter_bytes():
                        yield chunk
                except Exception as e:
                    print(f"⚠️ Error en stream: {e}")

            return StreamingResponse(iter_rd_content(), status_code=status_code, headers=content_headers)

    except Exception as e:
        print(f"❌ Error al hacer proxy: {e}")
        return PlainTextResponse("Internal Server Error", status_code=500)


if __name__ == "__main__":
    uvicorn.run("proxy_server:app", host="0.0.0.0", port=5000)
