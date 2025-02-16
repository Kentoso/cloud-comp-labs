from embedder import AbstractEmbedder
from pgvector.psycopg import register_vector
import psycopg
from abc import abstractmethod, ABC
import numpy as np


class AbstractSearcher(ABC):
    @abstractmethod
    def search(self, query: str) -> list[dict]:
        pass


class Searcher:
    def __init__(self, embedder: AbstractEmbedder, conn_str: str):
        self.embedder = embedder
        self.conn_str = conn_str

    def search(self, query: str) -> list[dict]:
        query_embedding = self.embedder.get_embeddings([query], task="RETRIEVAL_QUERY")[
            0
        ]
        query_embedding = np.array(query_embedding)

        with psycopg.connect(self.conn_str) as conn:
            register_vector(conn)

            # Search for the most similar embeddings using the cosine similarity
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, data, 1 - (embedding <=> %s) AS similarity
                    FROM embedded_data
                    WHERE 1 - (embedding <=> %s) > 0.5
                    ORDER BY similarity DESC
                    """,
                    (query_embedding, query_embedding),
                )
                rows = cur.fetchall()

        return [{"id": row[0], "data": row[1], "similarity": row[2]} for row in rows]
