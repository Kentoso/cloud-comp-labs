import pathlib
from dotenv import load_dotenv
import argparse
import requests
import pandas
import os
import psycopg

from preprocessor import Preprocessor
from summarizer import TfidfTextSummarizer
from embedder import Embedder
from psycopg.types.json import Jsonb
from pgvector.psycopg import register_vector
from searcher import Searcher

import tqdm

load_dotenv()

DATASET_URL = (
    "https://www.kaggle.com/api/v1/datasets/download/jrobischon/wikipedia-movie-plots"
)
DATASET_PATH = "data/wiki_movie_plots_deduped.csv"
DATASET_ROWS = 100
DATASET_EMBEDDING_COLUMN = "Plot"
PREPROCESSED_DATASET_PATH = f"data/processed_{DATASET_ROWS}.parquet"

POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING")


def get_image(page_title: str, thumb_size: int = 300):
    if not page_title or page_title == "#":
        return "No image found"

    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": page_title,
        "prop": "pageimages",
        "format": "json",
        "pithumbsize": thumb_size,
        "redirects": 1,
        "pilicense": "any",
    }
    response = requests.get(url, params=params)
    data = response.json()
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        thumbnail = page.get("thumbnail")
        if thumbnail:
            return thumbnail.get("source")
    return ""


def preprocess_dataset():
    df = pandas.read_csv(DATASET_PATH)

    # filter out rows with release year < 2000
    df = df[df["Release Year"] >= 2000]

    # sample DATASET_ROWS random rows
    df = df.sample(DATASET_ROWS, random_state=42)

    # get wiki thumbnails
    print("Getting wiki thumbnails")
    df["wiki_thumbnail"] = df["Wiki Page"].apply(
        lambda wiki_page_url: get_image(
            wiki_page_url.split("/")[-1] if "/" in wiki_page_url else wiki_page_url
        )
    )

    summarizer = TfidfTextSummarizer()

    preprocessor = Preprocessor(summarizer)

    df = preprocessor.preprocess(df, DATASET_EMBEDDING_COLUMN, max_words=300).head(
        DATASET_ROWS
    )

    embedder = Embedder()

    plot_summaries = df[f"{DATASET_EMBEDDING_COLUMN}_summary"].tolist()

    df[f"{DATASET_EMBEDDING_COLUMN}_summary_embedding"] = embedder.get_embeddings(
        plot_summaries
    )

    del df[f"{DATASET_EMBEDDING_COLUMN}_summary"]

    return df


def init_db():
    if not pathlib.Path(DATASET_PATH).exists():
        print(f"Download dataset from Kaggle: {DATASET_URL}, put it in {DATASET_PATH}")
        return

    print("Dataset exists, initializing database")
    if not pathlib.Path(PREPROCESSED_DATASET_PATH).exists():
        print("Preprocessing dataset")
        df = preprocess_dataset()
        df.to_parquet(PREPROCESSED_DATASET_PATH, index=False)
    else:
        print("Preprocessed dataset exists")
        df = pandas.read_parquet(PREPROCESSED_DATASET_PATH)

    df.fillna("", inplace=True)

    with psycopg.connect(POSTGRES_CONNECTION_STRING) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        register_vector(conn)

        with conn.cursor() as cur:
            cur.execute(
                """
                TRUNCATE embedded_data;
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS embedded_data (
                    id SERIAL PRIMARY KEY,
                    data JSONB,
                    embedding vector(768)
                )
                """
            )

            for _, row in tqdm.tqdm(df.iterrows()):
                data = {}
                for column in [c for c in df.columns if "_embedding" not in c]:
                    data[column] = row.loc[column]

                embedding_column = [c for c in df.columns if "_embedding" in c][0]

                cur.execute(
                    """
                    INSERT INTO embedded_data (data, embedding)
                    VALUES (%s, %s)
                    """,
                    (
                        Jsonb(data),
                        row.loc[embedding_column],
                    ),
                )

            conn.commit()

            # get how many inserted
            count = cur.execute("SELECT COUNT(*) FROM embedded_data").fetchone()

            print(f"Inserted {count} rows")


class Inputs:
    def __init__(self, init_db_flag):
        self.init_db_flag = init_db_flag


def handle_input():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize the database with the dataset",
    )
    args = parser.parse_args()
    init_db_flag = args.init_db

    return Inputs(init_db_flag)


def main():
    inputs = handle_input()

    if inputs.init_db_flag:
        init_db()
        print(
            "Database initialized. You can now run the UI by running main.py without options."
        )
        return

    from ui import MoviePlotSearchUI
    from nicegui import ui

    embedder = Embedder()
    searcher = Searcher(embedder, POSTGRES_CONNECTION_STRING)

    MoviePlotSearchUI(POSTGRES_CONNECTION_STRING, searcher)
    ui.run(dark=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()

# main()
