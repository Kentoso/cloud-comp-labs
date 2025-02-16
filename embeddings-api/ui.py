from nicegui import ui
import psycopg
import requests
from searcher import AbstractSearcher


class MoviePlotSearchUI:
    def __init__(self, conn_str: str, searcher: AbstractSearcher):
        self.init_ui()
        self.conn_str = conn_str
        self.searcher = searcher

        # with psycopg.connect(self.conn_str) as conn:
        #     with conn.cursor() as cur:
        #         cur.execute("SELECT id, data FROM embedded_data")
        #         rows = cur.fetchall()
        #         rows_dicts = [{"id": row[0], "data": row[1]} for row in rows]

        # self.set_cards(rows_dicts)

    def init_ui(self):
        with ui.column().style(
            "height: 100vh; width: 100%; display: flex; flex-direction: column; align-items: center; justify-content: start;"
        ):
            ui.label("Movie Plot Search").classes("text-h4 font-bold mb-4")

            with ui.grid(columns=2):
                self.search_input = ui.input(
                    placeholder="Enter search terms...",
                ).props("dense")
                self.search_btn = ui.button(
                    "Search", on_click=self.on_click_search
                ).props("dense")

            self.results_found = ui.label("Results found: 0").classes("text-caption")

            self.cards_container = ui.row().style(
                """
                margin-top: 20px;
                width: 95%;
                overflow-y: auto;
                flex-wrap: wrap;
                gap: 1rem;
                justify-content: center
                """
            )

    def set_cards(self, rows: list[dict]):
        self.cards_container.clear()
        self.results_found.set_text(f"Results found: {len(rows)}")
        self.results_found.update()
        print("Adding cards...")
        for row in rows:
            self.add_card(row)
            self.cards_container.update()

    def add_card(self, row: dict):
        data = row["data"]
        wiki_page_url = data.get("Wiki Page", "#")
        page_title = (
            wiki_page_url.split("/")[-1] if "/" in wiki_page_url else wiki_page_url
        )

        # img_url = self.get_image(page_title)
        img_url = data["wiki_thumbnail"]

        with self.cards_container:
            with ui.card().classes("q-pa-sm").style("width: 350px;"):
                if img_url and img_url != "No image found":
                    ui.image(img_url).style("max-width: 100%; height: auto;")

                plot_full = data.get("Plot", "No Plot Available")
                plot_short = plot_full
                is_truncated = False
                if len(plot_full) > 200:
                    plot_short = plot_full[:200] + "..."
                    is_truncated = True

                def build_markdown_content(show_full: bool) -> str:
                    plot_text = plot_full if show_full else plot_short
                    return f"""
#### **{data.get('Title', 'No Title')}**  
**Directed by**: {data.get('Director', 'Unknown')}

**Genre**: {data.get('Genre', 'N/A')}  
**Release Year**: {data.get('Release Year', 'N/A')}  
**Origin/Ethnicity**: {data.get('Origin/Ethnicity', 'N/A')}

[Wiki Page]({wiki_page_url})

**Plot**: {plot_text}
"""

                expanded = False
                md = ui.markdown(build_markdown_content(expanded)).classes("text-body1")

                # if is_truncated:

                #     def toggle_plot():
                #         nonlocal expanded
                #         expanded = not expanded
                #         md.set_content(build_markdown_content(expanded))
                #         toggle_btn.set_text("Show Less" if expanded else "Show More")

                #     toggle_btn = ui.button("Show More", on_click=toggle_plot).classes(
                #         "q-mt-sm"
                #     )

    def on_click_search(self):
        search_value = self.get_search_value()
        self.search(search_value)

    def search(self, search_value: str):
        print("Searching...", search_value)
        results = self.searcher.search(search_value)

        results_without_similarity = [
            {"id": row["id"], "data": row["data"]} for row in results
        ]

        print("Found", len(results_without_similarity), "results")

        self.set_cards(results_without_similarity)

    def get_search_value(self) -> str:
        return self.search_input.value
