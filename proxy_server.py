from flask import Flask, request, Response, abort
import requests

app = Flask(__name__)

@app.route('/stream', methods=["GET", "HEAD"])
def stream():
    rd_url = request.args.get("link")

    if not rd_url or not rd_url.startswith("https://"):
        print("❌ Error: 'link' faltante o inválido")
        return "Missing or invalid 'link' parameter", 400

    headers = {}
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header
        print(f"📡 Cliente solicitó rango: {range_header}")
    else:
        print("📡 Solicitud sin rango (GET completo o HEAD)")

    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    print(f"🌐 Cliente: {client_ip} | Método: {request.method}")
    print(f"🔗 Enlace solicitado: {rd_url}")

    try:
        rd_response = requests.request(
            method=request.method,
            url=rd_url,
            headers=headers,
            stream=True,
            timeout=10
        )

        print(f"✅ Real-Debrid respondió con HTTP {rd_response.status_code}")
        print("🧾 Headers recibidos de RD:")
        for k, v in rd_response.headers.items():
            print(f"   {k}: {v}")

        # Headers que se reenviarán al cliente (filtrados)
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

        # Asegura que haya Accept-Ranges al menos
        response_headers.setdefault("Accept-Ranges", "bytes")

        # Determina si es respuesta parcial o completa
        if "Content-Range" in rd_response.headers:
            status_code = 206
        else:
            status_code = 200

        # Si es HEAD, no se devuelve contenido
        if request.method == "HEAD":
            print("📭 Respuesta HEAD sin cuerpo")
            return Response(status=status_code, headers=response_headers)

        print(f"🚀 Iniciando stream hacia el cliente con HTTP {status_code}")
        return Response(
            rd_response.iter_content(chunk_size=8192),
            status=status_code,
            headers=response_headers
        )

    except Exception as e:
        print(f"❌ Error al hacer proxy del link {rd_url}: {e}")
        abort(500)


if __name__ == "__main__":
    print("🚀 Proxy Real-Debrid iniciando en puerto 5000...")
    app.run(host="0.0.0.0", port=5000)
