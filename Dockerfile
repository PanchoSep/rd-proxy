FROM python:3.11-slim

WORKDIR /app
COPY proxy_server.py /app

RUN pip install fastapi uvicorn aiohttp

CMD ["uvicorn", "rd_proxy:app", "--host", "0.0.0.0", "--port", "5000"]
