FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    CHROMA_DIR=/data/chroma \
    FLASHRANK_CACHE_DIR=/tmp/flashrank_models

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

# Bake Chroma ONNX embedding model and FlashRank model into image
RUN python -c "from chromadb.utils import embedding_functions; embedding_functions.DefaultEmbeddingFunction()"
RUN python -c "from flashrank import Ranker; Ranker(model_name='ms-marco-TinyBERT-L-2-v2', cache_dir='/tmp/flashrank_models')"

RUN mkdir -p /data/chroma /tmp/flashrank_models

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
