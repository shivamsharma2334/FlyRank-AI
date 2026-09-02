"""Build the FAISS index from kb/*.md. Run once, and again after editing the KB:
    cd backend && python scripts/build_index.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag_service import build_index

if __name__ == "__main__":
    build_index()
    print("FAISS index built and saved to data/faiss_index/")
