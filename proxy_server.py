from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, StreamingResponse, PlainTextResponse
import httpx
import uvicorn
from mimetypes import guess_type

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

    # 🎯 Detecta ffprobe desde localhost
    is_ffprobe = range_header == "bytes=0-" and client_ip == "127.0.0.1"
    if is_ffprobe:
        print("🎯 ffprobe detectado: redirigiendo directo")
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

                # Detectar content-type por extensión si RD da uno raro
                filename = rd_url.split("/")[-1]
                detected_type = guess_type(filename)[0] or "application/octet-stream"

                # Headers que reenviaremos (filtrados)
                safe_headers = {
                    k: v for k, v in rd_response.headers.items()
                    if k.lower() in [
                        "content-range",
                        "accept-ranges",
                        "cache-control",
                        "etag",
                        "last-modified",
                        "content-disposition"
                    ]
                }

                # Agregar Content-Length si está presente y seguro
                if "content-length" in rd_response.headers:
                    safe_headers["Content-Length"] = rd_response.headers["content-length"]

                status_code = 206 if "content-range" in rd_response.headers else 200

                async def iter_rd_content():
                    sent = 0
                    try:
                        async for chunk in rd_response.aiter_bytes():
                            sent += len(chunk)
                            yield chunk
                        print(f"✅ Stream finalizado, bytes enviados: {sent}")
                    except httpx.StreamClosed:
                        print(f"⚠️ Stream cerrado prematuramente por cliente, bytes enviados: {sent}")
                    except Exception as e:
                        print(f"❌ Error en stream: {e}")
                        raise

                return StreamingResponse(
                    iter_rd_content(),
                    status_code=status_code,
                    media_type=detected_type,
                    headers=safe_headers
                )

    except Exception as e:
        print(f"❌ Error al hacer proxy del link {rd_url}: {e}")
        return PlainTextResponse("Internal Server Error", status_code=500)


if __name__ == "__main__":
    print("🚀 Proxy Real-Debrid iniciando en puerto 5000...")
    uvicorn.run("proxy_server:app", host="0.0.0.0", port=5000)
