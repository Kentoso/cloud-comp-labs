import pandas as pd
from summarizer import AbstractTextSummarizer


class Preprocessor:
    def __init__(self, summarizer: AbstractTextSummarizer):
        self.summarizer = summarizer

    def preprocess(
        self, data: pd.DataFrame, embedding_column: str, max_words: int = 2000
    ) -> pd.DataFrame:
        data[f"{embedding_column}_summary"] = data[embedding_column].apply(
            lambda x: self.summarizer.summarize(x, max_words=max_words)
        )

        return data
