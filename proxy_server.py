from flask import Flask, request, Response, abort
import requests

app = Flask(__name__)

@app.route('/stream')
def stream():
    rd_url = request.args.get("link")
    if not rd_url or not rd_url.startswith("https://"):
        return "Missing or invalid 'link' parameter", 400

    headers = {}

    # Extraemos el header Range si existe
    range_header = request.headers.get('Range')
    if range_header:
        headers['Range'] = range_header
        print(f"➡️ Cliente pidió rango: {range_header}")

    try:
        # Pedimos el archivo a Real-Debrid con o sin rango
        rd_response = requests.get(rd_url, headers=headers, stream=True)

        # Pasamos headers relevantes al cliente
        response_headers = {
            'Content-Type': rd_response.headers.get('Content-Type', 'video/mp4'),
            'Content-Length': rd_response.headers.get('Content-Length', '0'),
            'Accept-Ranges': 'bytes',
        }

        # Si la respuesta incluye Content-Range, es parcial (206)
        if 'Content-Range' in rd_response.headers:
            response_headers['Content-Range'] = rd_response.headers['Content-Range']
            status_code = 206
        else:
            status_code = 200

        return Response(
            rd_response.iter_content(chunk_size=8192),
            status=status_code,
            headers=response_headers
        )

    except Exception as e:
        print(f"❌ Error al hacer proxy: {e}")
        abort(500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
