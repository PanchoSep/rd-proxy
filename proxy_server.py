from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse, PlainTextResponse
import httpx
import uvicorn

app = FastAPI()


@app.get("/stream")
async def stream(request: Request):
    rd_url = request.query_params.get("link")
    if not rd_url or not rd_url.startswith("https://"):
        print("❌ Error: 'link' faltante o inválido")
        return PlainTextResponse("Missing or invalid 'link' parameter", status_code=400)

    range_header = request.headers.get("Range", "")
    client_ip = request.client.host
    method = request.method

    print(f"🌐 Cliente: {client_ip} | Método: {method}")
    print(f"🔗 Enlace solicitado: {rd_url}")
    print(f"📡 Cliente solicitó rango: {range_header or 'SIN RANGO'}")

    # 🎯 Detección automática de ffprobe por rango
    is_ffprobe = range_header == "bytes=0-"
    if is_ffprobe:
        print("🎯 ffprobe detectado por rango: redirigiendo directo a RD")
        return RedirectResponse(rd_url)

    headers = {}
    if range_header:
        headers["Range"] = range_header

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            rd_response = await client.request(
                method=method,
                url=rd_url,
                headers=headers,
                follow_redirects=True,
                stream=True,
            )

            print(f"✅ Real-Debrid respondió con HTTP {rd_response.status_code}")
            print("🧾 Headers recibidos de RD:")
            for k, v in rd_response.headers.items():
                print(f"   {k}: {v}")

            # Headers que se reenviarán
            response_headers = {
                k: v for k, v in rd_response.headers.items()
                if k.lower() in [
                    "content-type",
                    "content-length",
                    "content-range",
                    "accept-ranges",
                    "cache-control",
                    "etag",
                    "last-modified"
                ]
            }
            response_headers.setdefault("Accept-Ranges", "bytes")

            status_code = 206 if "Content-Range" in rd_response.headers else 200
            return StreamingResponse(
                rd_response.aiter_bytes(),
                status_code=status_code,
                headers=response_headers
            )

    except Exception as e:
        print(f"❌ Error al hacer proxy del link {rd_url}: {e}")
        return PlainTextResponse("Internal Server Error", status_code=500)


if __name__ == "__main__":
    print("🚀 Proxy Real-Debrid iniciando en puerto 5000...")
    uvicorn.run("proxy_server:app", host="0.0.0.0", port=5000)
