from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.responses import StreamingResponse, RedirectResponse
import httpx
from urllib.parse import unquote

app = FastAPI()

@app.get("/stream")
async def stream(request: Request, link: str, background_tasks: BackgroundTasks):
    rd_url = unquote(link)
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    range_header = request.headers.get("range")

    headers = {}

    # ffprobe desde VPS → redirige
    is_ffprobe = range_header == "bytes=0-"
    is_vps = client_ip.startswith("127.") or client_ip == "128.140.93.28"

    if is_ffprobe and is_vps:
        print("🎯 ffprobe detectado DESDE VPS: redirigiendo directo a RD")
        return RedirectResponse(rd_url)

    if range_header:
        if "Lavf" in user_agent and is_ffprobe:
            print("🎯 Lavf externo detectado, forzando Range 0-1048575")
            headers["Range"] = "bytes=0-1048575"
        else:
            headers["Range"] = range_header

    try:
        client = httpx.AsyncClient(timeout=None)
        rd_stream_cm = client.stream("GET", rd_url, headers=headers)
        async with rd_stream_cm as rd_stream:
            rd_headers = dict(rd_stream.headers)

            print("✅ Real-Debrid respondió con", rd_stream.status_code)
            print("🧾 Headers recibidos de RD:")
            for k, v in rd_headers.items():
                print(f"   {k}: {v}")

            content_type = rd_headers.get("content-type", "application/octet-stream")
            content_disposition = rd_headers.get("content-disposition")

            if content_type == "application/force-download":
                content_type = "video/x-matroska"
                print("🔧 Corrigiendo content-type a video/x-matroska")

            if content_disposition:
                print("🧹 Eliminando content-disposition")
                del rd_headers["content-disposition"]

            response_headers = {
                k: v for k, v in rd_headers.items()
                if k.lower() not in ["content-encoding", "transfer-encoding"]
            }
            response_headers["content-type"] = content_type

            background_tasks.add_task(rd_stream.aclose)

            return StreamingResponse(
                rd_stream.aiter_bytes(),
                status_code=rd_stream.status_code,
                headers=response_headers,
                background=background_tasks,
            )

    except Exception as e:
        print(f"❌ Error al hacer proxy del link {rd_url}: {e}")
        return Response(content="Error al hacer proxy del archivo.", status_code=500)
