"""
RAG (Retrieval-Augmented) pipeline for voice commands.

Runs after voice detection / ASR. Indexes intent and action layers dynamically,
strips filler words, and returns a clean command string for the intent parser
and action engine.

Auto-updates: the index is refreshed automatically when intent/constants.py,
intent/parser.py, or any .py in actions/ is modified (by file mtime), so new
intents or actions are picked up without restarting the app.

Usage:
    from rag import RAGPipeline

    pipeline = RAGPipeline()
    cleaned = pipeline.normalize("can you like open chrome please")
    # -> "open chrome"
    pipeline.refresh_index()  # optional: force refresh after changes
"""

from .pipeline import RAGPipeline

__all__ = ["RAGPipeline"]
