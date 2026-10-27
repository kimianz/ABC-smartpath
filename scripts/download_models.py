"""One-time free model downloads. Subsequent startup uses cached models."""
import os
from sentence_transformers import SentenceTransformer,CrossEncoder
SentenceTransformer(os.getenv('EMBEDDING_MODEL','sentence-transformers/all-MiniLM-L6-v2'),device='cpu')
CrossEncoder(os.getenv('RERANK_MODEL','cross-encoder/ms-marco-MiniLM-L6-v2'),device='cpu')
print('Local embedding and reranking models cached.')
