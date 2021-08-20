from contrib.utils import append_url


class TestAppendUrl:
    def test_1(self):
        server = "http://directory.abigbot.com/"
        url = "/wp-json/bigbot/v1/posts"
        added = append_url(server, url)
        assert added == "http://directory.abigbot.com/wp-json/bigbot/v1/posts"

    def test_2(self):
        server = "http://directory.abigbot.com"
        url = "/wp-json/bigbot/v1/posts"
        added = append_url(server, url)
        assert added == "http://directory.abigbot.com/wp-json/bigbot/v1/posts"

    def test_3(self):
        server = "http://directory.abigbot.com"
        url = "wp-json/bigbot/v1/posts"
        added = append_url(server, url)
        assert added == "http://directory.abigbot.com/wp-json/bigbot/v1/posts"
