from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, PlainTextResponse
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
    user_agent = request.headers.get("User-Agent", "unknown")
    method = request.method

    print(f"🌐 Cliente: {client_ip} | Método: {method}")
    print(f"🔗 Enlace solicitado: {rd_url}")
    print(f"📡 Cliente solicitó rango: {range_header or 'SIN RANGO'}")
    print(f"🧭 User-Agent: {user_agent}")

    is_ffprobe = range_header == "bytes=0-"
    is_vps = client_ip.startswith("127.") or client_ip == "128.140.93.28"

    if is_ffprobe and is_vps:
        print("🎯 ffprobe detectado DESDE VPS: redirigiendo directo a RD")
        return RedirectResponse(rd_url)

    headers = {}
    if range_header:
        headers["Range"] = range_header

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                method=method,
                url=rd_url,
                headers=headers,
                follow_redirects=True,
            ) as rd_response:

                print(f"✅ Real-Debrid respondió con HTTP {rd_response.status_code}")
                print("🧾 Headers recibidos de RD:")
                for k, v in rd_response.headers.items():
                    print(f"   {k}: {v}")

                # Solo los headers relevantes
                response_headers = {
                    k: v for k, v in rd_response.headers.items()
                    if k.lower() in [
                        "content-type",
                        "content-length",
                        "content-range",
                        "accept-ranges",
                        "cache-control",
                        "etag",
                        "last-modified",
                    ]
                }

                # ⚠️ Corrige content-type si es inválido
                if response_headers.get("content-type") == "application/force-download":
                    response_headers["content-type"] = "video/x-matroska"

                # Asegurar que acepte Range
                response_headers.setdefault("Accept-Ranges", "bytes")

                status_code = 206 if "content-range" in rd_response.headers else 200

                # 🔁 Streaming manual controlado
                async def send_body(scope, receive, send):
                    await send({
                        "type": "http.response.start",
                        "status": status_code,
                        "headers": [
                            (k.encode("latin-1"), v.encode("latin-1"))
                            for k, v in response_headers.items()
                        ],
                    })

                    async for chunk in rd_response.aiter_bytes():
                        await send({
                            "type": "http.response.body",
                            "body": chunk,
                            "more_body": True,
                        })

                    await send({
                        "type": "http.response.body",
                        "body": b"",
                        "more_body": False,
                    })

                return send_body

    except Exception as e:
        print(f"❌ Error al hacer proxy del link {rd_url}: {e}")
        return PlainTextResponse("Internal Server Error", status_code=500)


if __name__ == "__main__":
    print("🚀 Proxy Real-Debrid iniciando en puerto 5000...")
    uvicorn.run("proxy_server:app", host="0.0.0.0", port=5000)
