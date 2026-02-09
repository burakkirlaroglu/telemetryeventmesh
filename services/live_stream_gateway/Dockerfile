FROM python:3.12-slim

WORKDIR /app

RUN pip install fastapi "uvicorn[standard]" redis

COPY app /app

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
