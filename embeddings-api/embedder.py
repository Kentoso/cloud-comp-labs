from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
import time
from abc import abstractmethod, ABC


class AbstractEmbedder(ABC):
    @abstractmethod
    def get_embeddings(self, texts: list[str], model: str, task: str) -> list:
        pass


class Embedder:
    def get_embeddings(
        self,
        texts: list[str],
        model: str = "text-embedding-005",
        task: str = "RETRIEVAL_DOCUMENT",
    ) -> list:
        model = TextEmbeddingModel.from_pretrained(model)
        result = []
        batch_size = 45
        cursor = 0

        if len(texts) < batch_size:
            inputs = [TextEmbeddingInput(text=text, task_type=task) for text in texts]
            embeddings = model.get_embeddings(inputs)
            return [embedding.values for embedding in embeddings]

        while cursor - batch_size < len(texts):
            current_texts = texts[cursor : cursor + batch_size]
            if len(current_texts) == 0:
                break
            inputs = [
                TextEmbeddingInput(text=text, task_type=task) for text in current_texts
            ]
            embeddings = model.get_embeddings(inputs)
            result.extend([embedding.values for embedding in embeddings])
            cursor += batch_size
            time.sleep(5)

        return result
