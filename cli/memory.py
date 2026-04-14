import time
import uuid
from pathlib import Path
from loguru import logger

try:
    import chromadb
except ImportError:
    chromadb = None

from cli.embedder import get_embedding, embed_finding

MEMORY_DIR = "data/memory"


class ReviewMemory:
    def __init__(self, memory_dir: str = MEMORY_DIR) -> None:
        if chromadb is None:
            raise ImportError("chromadb is required. Run: pip install chromadb")
        Path(memory_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=memory_dir)
        self._findings = self._client.get_or_create_collection("findings")

    def store_finding(self, filepath: str, finding: dict,
                      verdict: str = "pending") -> None:
        try:
            text = embed_finding(finding)
            embedding = get_embedding(text)
            doc_id = str(uuid.uuid4())
            line = finding.get("line")
            self._findings.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[{
                    "filepath": filepath,
                    "line": int(line) if isinstance(line, int) else -1,
                    "severity": finding.get("severity") or "",
                    "type": finding.get("type") or "",
                    "verdict": verdict,
                    "timestamp": time.time(),
                }],
            )
        except Exception as e:
            logger.warning(f"store_finding failed for {filepath}: {e}")

    def query_similar(self, finding: dict, n_results: int = 5) -> list[dict]:
        try:
            text = embed_finding(finding)
            embedding = get_embedding(text)
            results = self._findings.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["metadatas", "distances"],
            )
            output = []
            for meta, dist in zip(
                results["metadatas"][0], results["distances"][0]
            ):
                output.append({**meta, "distance": dist})
            return output
        except Exception as e:
            logger.warning(f"query_similar failed: {e}")
            return []

    def is_false_positive(self, finding: dict, filepath: str,
                          threshold: float = 0.85) -> bool:
        try:
            similar = self.query_similar(finding)
            for item in similar:
                if (
                    item.get("filepath") == filepath
                    and item.get("verdict") == "false_positive"
                    and item.get("distance", 1.0) < threshold
                ):
                    return True
            return False
        except Exception as e:
            logger.warning(f"is_false_positive failed: {e}")
            return False

    def get_codebase_patterns(self) -> list[str]:
        try:
            all_items = self._findings.get(include=["documents"])
            freq: dict[str, int] = {}
            for doc in all_items.get("documents") or []:
                freq[doc] = freq.get(doc, 0) + 1
            return [doc for doc, count in freq.items() if count >= 3]
        except Exception as e:
            logger.warning(f"get_codebase_patterns failed: {e}")
            return []

    def get_related_files(self, filepath: str) -> list[str]:
        try:
            items = self._findings.get(
                where={"filepath": filepath},
                include=["embeddings"],
            )
            embeddings = items.get("embeddings") or []
            if not embeddings:
                return []
            results = self._findings.query(
                query_embeddings=embeddings[:3],
                n_results=5,
                include=["metadatas"],
            )
            related = set()
            for meta_list in results.get("metadatas") or []:
                for meta in meta_list:
                    fp = meta.get("filepath", "")
                    if fp and fp != filepath:
                        related.add(fp)
            return list(related)
        except Exception as e:
            logger.warning(f"get_related_files failed: {e}")
            return []

    def mark_false_positive(self, filepath: str, line: int) -> None:
        try:
            results = self._findings.get(
                where={"filepath": filepath, "line": line},
                include=["metadatas"],
            )
            ids = results.get("ids") or []
            metadatas = results.get("metadatas") or []
            for doc_id, existing_meta in zip(ids, metadatas):
                updated_meta = {**existing_meta, "verdict": "false_positive"}
                self._findings.update(
                    ids=[doc_id],
                    metadatas=[updated_meta],
                )
        except Exception as e:
            logger.warning(f"mark_false_positive failed: {e}")

    def clear(self) -> None:
        try:
            self._client.delete_collection("findings")
            self._findings = self._client.get_or_create_collection("findings")
        except Exception as e:
            logger.warning(f"clear failed: {e}")