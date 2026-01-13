"""
Centralized AI/vector helpers for Open Educational Resourcer.

Configuration (via `.env` or Django settings):
    EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2          # or any compatible HF repo/id/path
    VECTOR_BACKEND=pgvector                        # or 'qdrant'
    QDRANT_URL=http://qdrant:6333

All model and vector DB access should use these helpers!
"""

import os
from resources.models import OERResource

# Singleton pattern for model & vector client
_MODEL = None
_VECTOR_CLIENT = None

def get_embedding_model():
    global _MODEL
    if _MODEL is None:
        # Model name is now configurable!
        from sentence_transformers import SentenceTransformer
        model_name = os.environ.get('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
        _MODEL = SentenceTransformer(model_name)
    return _MODEL

def get_vector_db_client():
    """
    Switchable vector DB client: 'pgvector' (direct, recommended default),
    'qdrant' (via HTTP API), or others.
    """
    global _VECTOR_CLIENT
    backend = os.environ.get('VECTOR_BACKEND', 'pgvector').lower()
    if backend == 'qdrant':
        if _VECTOR_CLIENT is None:
            from qdrant_client import QdrantClient
            qdrant_url = os.environ.get('QDRANT_URL', 'http://localhost:6333')
            _VECTOR_CLIENT = QdrantClient(url=qdrant_url)
        return _VECTOR_CLIENT
    # For 'pgvector' backend, the Django ORM and VectorField are used directly.
    return None

def generate_embeddings(batch_size=50):
    """
    Compute and store embeddings for all OERResources missing one.
    Only uses the embedding model (vector DB indexing handled elsewhere).
    """
    model = get_embedding_model()
    qs = OERResource.objects.filter(content_embedding__isnull=True)

    total = qs.count()
    for start in range(0, total, batch_size):
        batch = list(qs[start:start + batch_size])
        # Prefer extracted_text where available
        texts = []
        for r in batch:
            if getattr(r, 'extracted_text', None):
                texts.append(str(r.extracted_text))  # Ensure string
            else:
                # Ensure both parts are strings, handle None gracefully
                title = str(r.title) if r.title else ""
                description = str(r.description) if r.description else ""
                texts.append(f"{title} {description}")
        
        embeddings = model.encode(texts, show_progress_bar=False)
        for resource, emb in zip(batch, embeddings):
            try:
                resource.content_embedding = emb.tolist() if hasattr(emb, 'tolist') else list(emb)
                resource.save()
            except Exception:
                continue
    # (Optional: index in Qdrant if that's the configured backend)
    if os.environ.get('VECTOR_BACKEND', 'pgvector') == 'qdrant':
        client = get_vector_db_client()
        # TODO: implement batch upsert to Qdrant if desired


def compute_and_store_embedding_for_resource(resource_id):
    """
    Compute and store embedding for a single resource.
    If using external vector DB (e.g. Qdrant), index as well.
    """
    try:
        resource = OERResource.objects.get(id=resource_id)
    except OERResource.DoesNotExist:
        return False

    model = get_embedding_model()
    # Prefer extracted_text if present, ensure string type
    if getattr(resource, 'extracted_text', None):
        text = str(resource.extracted_text)
    else:
        title = str(resource.title) if resource.title else ""
        description = str(resource.description) if resource.description else ""
        text = f"{title} {description}"
    
    emb = model.encode([text])[0]
    try:
        resource.content_embedding = emb.tolist() if hasattr(emb, 'tolist') else list(emb)
        resource.save()
        if os.environ.get('VECTOR_BACKEND', 'pgvector') == 'qdrant':
            client = get_vector_db_client()
            # TODO: upsert just this record in Qdrant here
        return True
    except Exception:
        return False


def get_llm_client():
    """
    Get configured LLM client (Ollama or OpenAI).
    Configuration via .env:
      LLM_PROVIDER=ollama|openai
      OLLAMA_BASE_URL=http://host.docker.internal:11434  # Use host.docker.internal for Docker
      OLLAMA_MODEL=llama3.2:latest
      OPENAI_API_KEY=sk-...
    """
    provider = os.environ.get('LLM_PROVIDER', 'ollama').lower()
    
    if provider == 'ollama':
        try:
            # Use the new langchain-ollama package
            from langchain_ollama import OllamaLLM
            base_url = os.environ.get('OLLAMA_BASE_URL', 'http://host.docker.internal:11434')
            model = os.environ.get('OLLAMA_MODEL', 'llama3.2:latest')
            
            # Test connection
            llm = OllamaLLM(base_url=base_url, model=model, timeout=30)
            return llm
            
        except ImportError:
            raise ImportError(
                "langchain-ollama is not installed. "
                "Install it with: pip install langchain-ollama"
            )
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {base_url}. "
                f"Make sure Ollama is running and accessible from Docker. "
                f"Error: {str(e)}"
            )
    
    elif provider == 'openai':
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
                temperature=0.3
            )
        except ImportError:
            raise ImportError(
                "langchain_openai is not installed. "
                "Install it with: pip install langchain-openai"
            )
    
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
