import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from abc import abstractmethod, ABC


class AbstractTextSummarizer(ABC):
    @abstractmethod
    def summarize(self, text, max_words=100):
        pass


class TfidfTextSummarizer:
    def __init__(self, **vectorizer_kwargs):
        nltk.download("punkt_tab", quiet=True)
        self.vectorizer = TfidfVectorizer(**vectorizer_kwargs)

    def summarize(self, text, max_words=100):
        sentences = nltk.sent_tokenize(text)
        if not sentences:
            return ""

        total_words = sum(len(s.split()) for s in sentences)
        if total_words <= max_words:
            return text

        tfidf_matrix = self.vectorizer.fit_transform(sentences)
        sentence_scores = tfidf_matrix.sum(axis=1).A1

        # Create a list of tuples: (original index, sentence, score, word count)
        sentence_data = [
            (i, sentence, sentence_scores[i], len(sentence.split()))
            for i, sentence in enumerate(sentences)
        ]

        sentence_data.sort(key=lambda x: x[2], reverse=True)

        selected = []
        current_word_count = 0

        for idx, sentence, score, word_count in sentence_data:
            if current_word_count + word_count <= max_words:
                selected.append((idx, sentence))
                current_word_count += word_count

        selected.sort(key=lambda x: x[0])
        summary = " ".join(sentence for idx, sentence in selected)
        return summary
