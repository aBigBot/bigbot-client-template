import requests

from main.Component import DataExchange, SkillProvider
from main.Node import PreviewNode
from main.Statement import OutputStatement


# from main.Intent import Intent


# class GetRandomPageIntent(Intent):
#     def __init__(self):
#         super().__init__([[{"LEMMA": {"IN": ["random", "show"]}}]])


# class SearchIntent(Intent):
#     def __init__(self):
#         super().__init__(
#             [
#                 [
#                     {"LEMMA": {"IN": ["find", "how", "search", "what", "who"]}},
#                     {"LEMMA": "be", "OP": "?"},
#                 ]
#             ]
#         )  #


class WikipediaDESearch(DataExchange):
    def call(self, binder, operator_id, package, data, **kwargs):
        query = kwargs.get("query", "")

        if type(query) == list:
            if len(query) > 0:
                query = query[0]
            else:
                query = ""

        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "format": "json",
                "limit": 2,
                "search": query,
            },
        )
        data = response.json()
        url = data[3][0]

        output = OutputStatement(operator_id)
        output.append_node(PreviewNode(url))
        binder.post_message(output)

        return {"page_link": url}


class WikipediaSkillProvider(SkillProvider):
    pass
