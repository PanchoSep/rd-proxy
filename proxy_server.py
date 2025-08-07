from flask import Flask, request, Response, abort
import requests

app = Flask(__name__)

@app.route('/stream', methods=["GET", "HEAD"])
def stream():
    # Extrae el parámetro "link" desde la URL
    rd_url = request.args.get("link")

    if not rd_url or not rd_url.startswith("https://"):
        print("❌ Error: 'link' faltante o inválido")
        return "Missing or invalid 'link' parameter", 400

    # Prepara headers para reenviar al host de Real-Debrid
    headers = {}
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header
        print(f"📡 Recibida solicitud con rango: {range_header}")
    else:
        print("📡 Solicitud sin rango (stream completo o HEAD)")

    try:
        # Forward del request original a Real-Debrid, respetando método y headers
        rd_response = requests.request(
            method=request.method,
            url=rd_url,
            headers=headers,
            stream=True,
            timeout=10
        )

        # Construye los headers que se enviarán al cliente (Jellyfin o Infuse)
        response_headers = {
            "Content-Type": rd_response.headers.get("Content-Type", "video/mp4"),
            "Content-Length": rd_response.headers.get("Content-Length", "0"),
            "Accept-Ranges": "bytes",
        }

        # Si RD respondió con un rango parcial, propágalo al cliente
        if "Content-Range" in rd_response.headers:
            response_headers["Content-Range"] = rd_response.headers["Content-Range"]
            status_code = 206
        else:
            status_code = 200

        # Log del tipo de respuesta
        print(f"✅ [{request.remote_addr}] {request.method} {rd_url} → HTTP {status_code}")

        # Si el request fue HEAD, solo devuelve los headers
        if request.method == "HEAD":
            return Response(status=status_code, headers=response_headers)

        # Para GET, se retorna el contenido por chunks (streaming real)
        return Response(
            rd_response.iter_content(chunk_size=8192),
            status=status_code,
            headers=response_headers
        )

    except Exception as e:
        print(f"❌ Error al hacer proxy del link {rd_url}: {e}")
        abort(500)


if __name__ == "__main__":
    print("🚀 Iniciando proxy Real-Debrid en puerto 5000...")
    app.run(host="0.0.0.0", port=5000)
