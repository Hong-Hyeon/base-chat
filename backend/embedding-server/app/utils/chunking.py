from __future__ import annotations

from typing import Dict, List, Any

from app.utils.logger import get_logger


class TextChunker:
    """Utility for splitting text into manageable chunks for embeddings.

    Default strategy is character-length chunking with paragraph-aware boundaries and overlap.
    """

    def __init__(self, max_chars: int = 1500, overlap_chars: int = 200):
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")
        if overlap_chars < 0:
            raise ValueError("overlap_chars must be non-negative")
        if overlap_chars >= max_chars:
            raise ValueError("overlap_chars must be smaller than max_chars")

        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.logger = get_logger("text_chunker")

    def chunk_text(self, text: str) -> List[str]:
        """Split a long string into chunks.

        - Respects double-newline paragraph boundaries when possible
        - Adds `overlap_chars` characters of context between chunks
        """
        if not text:
            return [""]

        paragraphs = self._split_into_paragraphs(text)
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for paragraph in paragraphs:
            para_len = len(paragraph)
            if para_len > self.max_chars:
                # Paragraph is too long; hard-split by max_chars
                hard_parts = self._split_hard(paragraph)
                for part in hard_parts:
                    if current_len + len(part) + 1 > self.max_chars and current:
                        chunks.append("\n".join(current))
                        current = [self._tail_overlap(chunks[-1])]
                        current_len = len(current[0])
                    current.append(part)
                    current_len += len(part) + 1
                continue

            if current_len + para_len + 1 > self.max_chars and current:
                chunks.append("\n".join(current))
                current = [self._tail_overlap(chunks[-1])]
                current_len = len(current[0])

            current.append(paragraph)
            current_len += para_len + 1

        if current:
            chunks.append("\n".join(current))

        return [c.strip() for c in chunks if c is not None]

    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chunk a list of parsed document dicts with keys: content, metadata, source, mime_type.

        Returns same structure but with chunked entries and chunk metadata.
        """
        chunked: List[Dict[str, Any]] = []
        for doc in documents:
            content = doc.get("content", "")
            chunks = self.chunk_text(content)
            total = len(chunks)
            for idx, chunk in enumerate(chunks):
                meta = dict(doc.get("metadata") or {})
                meta.update({
                    "chunk_index": idx,
                    "num_chunks": total,
                })
                chunked.append({
                    "content": chunk,
                    "metadata": meta,
                    "source": doc.get("source"),
                    "mime_type": doc.get("mime_type"),
                })
        return chunked

    # ------------------------- internals -------------------------
    def _split_into_paragraphs(self, text: str) -> List[str]:
        # Normalize newlines and split on two-or-more newlines
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        parts: List[str] = []
        buffer: List[str] = []
        empty_streak = 0

        for line in normalized.split("\n"):
            if line.strip() == "":
                empty_streak += 1
                if empty_streak >= 1 and buffer:
                    parts.append("\n".join(buffer).strip())
                    buffer = []
                continue
            empty_streak = 0
            buffer.append(line)

        if buffer:
            parts.append("\n".join(buffer).strip())

        # Ensure no empty strings
        return [p for p in parts if p]

    def _split_hard(self, paragraph: str) -> List[str]:
        parts: List[str] = []
        start = 0
        while start < len(paragraph):
            end = min(start + self.max_chars, len(paragraph))
            parts.append(paragraph[start:end])
            start = end
        return parts

    def _tail_overlap(self, previous_chunk: str) -> str:
        if self.overlap_chars == 0 or not previous_chunk:
            return ""
        return previous_chunk[-self.overlap_chars :]


__all__ = ["TextChunker"]
