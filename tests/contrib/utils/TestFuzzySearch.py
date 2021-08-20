from contrib.utils import fuzzy_search


class TestFuzzySearch:
    def test_empty_hay(self):
        similarity, substring = fuzzy_search("test", "")
        assert similarity == 0.0
        assert substring == ""

    def test_empty_needle(self):
        similarity, substring = fuzzy_search("", "test")
        assert similarity == 1.0
        assert substring == ""

    def test_empty_string(self):
        similarity, substring = fuzzy_search("", "")
        assert similarity == 0.0
        assert substring == ""

    def test_simple(self):
        string = "The quick brown fox jumps over the lazy dog"
        _, substring = fuzzy_search("brawn", string)
        assert substring == "brown"

    def test_extra_characters(self):
        string = "The quick \tbrown! fox!!! jumps over, the lazy dog?"
        _, substring = fuzzy_search("brawn", string)
        assert substring == "brown"

    def test_not_found(self):
        string = "Buffalo buffalo Buffalo buffalo buffalo buffalo Buffalo buffalo"
        similarity, substring = fuzzy_search("test", string)
        print(similarity, substring)
        assert similarity == 0.0
        assert substring == ""
