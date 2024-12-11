import os

THRESHOLD = 0.22
MAX_CONCURRENT_TASKS = 10

# Load pre-computed face index and metadata
INDEX_PATH = "face_index.bin"
METADATA_PATH = "metadata.npy"

try:
    import faiss
    import numpy as np
    index = faiss.read_index(INDEX_PATH)
    metadata = np.load(METADATA_PATH)
except Exception as e:
    raise RuntimeError(f"Failed to load face recognition resources: {e}")
