from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, StreamingResponse, PlainTextResponse
import httpx
import uvicorn
from mimetypes import guess_type

app = FastAPI()
MAX_BYTES_FOR_PROBE = 5 * 1024 * 1024  # 5 MB


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

    # Redirige si es ffprobe desde localhost
    if range_header == "bytes=0-" and client_ip == "127.0.0.1":
        print("🎯 ffprobe desde localhost detectado: redirigiendo directo")
        return RedirectResponse(rd_url)

    headers = {}
    if range_header:
        headers["Range"] = range_header

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
            async with client.stream("GET", rd_url, headers=headers) as rd_response:
                print(f"✅ Real-Debrid respondió con HTTP {rd_response.status_code}")
                print("🧾 Headers de RD:")
                for k, v in rd_response.headers.items():
                    print(f"   {k}: {v}")

                # Detectar media_type por extensión
                filename = rd_url.split("/")[-1]
                detected_type = guess_type(filename)[0] or "application/octet-stream"

                # Headers seguros (NO reenviar Content-Length ni Connection)
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
                safe_headers.setdefault("Accept-Ranges", "bytes")

                status_code = 206 if "content-range" in rd_response.headers else 200

                # Detectar si es ffprobe
                is_ffprobe = (
                    range_header == "bytes=0-"
                    and user_agent.startswith("Lavf/")
                )
                max_bytes = MAX_BYTES_FOR_PROBE if is_ffprobe else None
                if is_ffprobe:
                    print(f"🎯 ffprobe detectado por User-Agent: entregando solo primeros {MAX_BYTES_FOR_PROBE} bytes")

                async def iter_rd_content():
                    sent = 0
                    try:
                        async for chunk in rd_response.aiter_bytes():
                            if not chunk:
                                continue
                            if max_bytes is not None:
                                remaining = max_bytes - sent
                                if remaining <= 0:
                                    print(f"✅ Corte después de {sent} bytes (ffprobe)")
                                    break
                                if len(chunk) > remaining:
                                    chunk = chunk[:remaining]
                            sent += len(chunk)
                            yield chunk
                        print(f"✅ Transmisión finalizada, bytes enviados: {sent}")
                    except httpx.StreamClosed:
                        print(f"⚠️ Cliente cerró conexión prematuramente. Bytes enviados: {sent}")
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
        print(f"❌ Error en el proxy: {e}")
        return PlainTextResponse("Internal Server Error", status_code=500)


if __name__ == "__main__":
    print("🚀 Proxy Real-Debrid iniciando en puerto 5000...")
    uvicorn.run("proxy_server:app", host="0.0.0.0", port=5000)
