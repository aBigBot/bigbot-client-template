from apps.wikipedia.component import WikipediaDESearch
from main.Config import AppConfig


class Application(AppConfig):
    def registry(self):
        # self.register(WikipediaSkillProvider)
        # self.link_intent(GetRandomPageIntent, WikipediaSkillProvider, kwargs={"method": "random"})
        # self.link_intent(SearchIntent, WikipediaSkillProvider, kwargs={"metdhod": "search"})
        self.register_data_exchange(
            WikipediaDESearch,
            "Wikipedia Search",
            "Wikipedia Search",
            input=[
                {
                    "description": "Search Query",
                    "name": "query",
                    "readable": "Search Query",
                    "type": "str"
                }
            ],
            output=[
                {
                    "description": "Link to Wikipedia page",
                    "name": "page_link",
                    "readable": "Page Link",
                    "type": "url"
                }
            ]
        )
