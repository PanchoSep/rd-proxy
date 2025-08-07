from fastapi import FastAPI, Request
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
    user_agent = request.headers.get("User-Agent", "N/A")

    print(f"🛰️ User-Agent: {user_agent}")
    print(f"🌐 Cliente: {client_ip} | Método: {method}")
    print(f"🔗 Enlace solicitado: {rd_url}")
    print(f"📡 Cliente solicitó rango: {range_header or 'SIN RANGO'}")

    # 🎯 Detecta si es ffprobe desde localhost y redirige
    is_ffprobe = range_header == "bytes=0-" and client_ip == "127.0.0.1"
    if is_ffprobe:
        print("🎯 ffprobe detectado por rango desde localhost: redirigiendo directo a RD")
        return RedirectResponse(rd_url)

    headers = {}
    if range_header:
        headers["Range"] = range_header

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
            async with client.stream("GET", rd_url, headers=headers) as rd_response:
                print(f"✅ Real-Debrid respondió con HTTP {rd_response.status_code}")
                print("🧾 Headers recibidos de RD:")
                for k, v in rd_response.headers.items():
                    print(f"   {k}: {v}")

                # Reenviar solo los headers seguros (sin Content-Length)
                response_headers = {
                    k: v for k, v in rd_response.headers.items()
                    if k.lower() in [
                        "content-type",
                        "content-range",
                        "accept-ranges",
                        "cache-control",
                        "etag",
                        "last-modified",
                        "content-disposition"
                    ]
                }
                response_headers.setdefault("Accept-Ranges", "bytes")

                status_code = 206 if "content-range" in rd_response.headers else 200

                async def iter_rd_content():
                    try:
                        async for chunk in rd_response.aiter_bytes():
                            yield chunk
                    except httpx.StreamClosed:
                        print("⚠️ Stream cerrado por el cliente (posiblemente Infuse reanudando)")
                    except Exception as e:
                        print(f"❌ Error en iteración del stream: {e}")
                        raise

                return StreamingResponse(
                    iter_rd_content(),
                    status_code=status_code,
                    media_type=rd_response.headers.get("content-type", "application/octet-stream"),
                    headers=response_headers
                )

    except Exception as e:
        print(f"❌ Error al hacer proxy del link {rd_url}: {e}")
        return PlainTextResponse("Internal Server Error", status_code=500)


if __name__ == "__main__":
    print("🚀 Proxy Real-Debrid iniciando en puerto 5000...")
    uvicorn.run("proxy_server:app", host="0.0.0.0", port=5000)
