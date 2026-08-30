FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    CHROMA_DIR=/data/chroma

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

# Bake ONNX embedding model into image so container starts without downloading at runtime
RUN python -c "from chromadb.utils import embedding_functions; embedding_functions.DefaultEmbeddingFunction()"

RUN mkdir -p /data/chroma

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
