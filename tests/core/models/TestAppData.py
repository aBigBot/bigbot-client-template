import pytest

from core.models import AppData


class TestBoolType:
    @pytest.mark.django_db
    def test_default_value(self):
        AppData.put_data("test", "test", type_=bool)
        data = AppData.get_data("test", "test")
        assert data == False

    @pytest.mark.django_db
    def test_false_value(self):
        AppData.put_data("test", "test", False, bool)
        data = AppData.get_data("test", "test")
        assert data == False

    @pytest.mark.django_db
    def test_true_value(self):
        AppData.put_data("test", "test", True, bool)
        data = AppData.get_data("test", "test")
        assert data == True

    @pytest.mark.django_db
    def test_invalid_value(self):
        AppData.put_data("test", "test", "invalid", bool)
        data = AppData.get_data("test", "test")
        assert data == False


class TestDictType:
    @pytest.mark.django_db
    def test_default_value(self):
        AppData.put_data("test", "test", type_=dict)
        data = AppData.get_data("test", "test")
        assert data == {}

    @pytest.mark.django_db
    def test_valid_value(self):
        AppData.put_data("test", "test", {"test": "test"}, dict)
        data = AppData.get_data("test", "test")
        assert data == {"test": "test"}

    @pytest.mark.django_db
    def test_invalid_value(self):
        AppData.put_data("test", "test", "invalid", dict)
        data = AppData.get_data("test", "test")
        assert data == {}


class TestFloatType:
    @pytest.mark.django_db
    def test_default_value(self):
        AppData.put_data("test", "test", type_=float)
        data = AppData.get_data("test", "test")
        assert data == 0.0

    @pytest.mark.django_db
    def test_valid_value(self):
        AppData.put_data("test", "test", 1.5, float)
        data = AppData.get_data("test", "test")
        assert data == 1.5

    @pytest.mark.django_db
    def test_invalid_value(self):
        AppData.put_data("test", "test", "invalid", float)
        data = AppData.get_data("test", "test")
        assert data == 0.0


class TestIntType:
    @pytest.mark.django_db
    def test_default_value(self):
        AppData.put_data("test", "test", type_=int)
        data = AppData.get_data("test", "test")
        assert data == 0

    @pytest.mark.django_db
    def test_valid_value(self):
        AppData.put_data("test", "test", 1, int)
        data = AppData.get_data("test", "test")
        assert data == 1

    @pytest.mark.django_db
    def test_invalid_value(self):
        AppData.put_data("test", "test", "invalid", int)
        data = AppData.get_data("test", "test")
        assert data == 0


class TestListType:
    @pytest.mark.django_db
    def test_default_value(self):
        AppData.put_data("test", "test", type_=list)
        data = AppData.get_data("test", "test")
        assert data == []

    @pytest.mark.django_db
    def test_valid_value(self):
        AppData.put_data("test", "test", [1, 2, 3], list)
        data = AppData.get_data("test", "test")
        assert data == [1, 2, 3]

    @pytest.mark.django_db
    def test_invalid_value(self):
        AppData.put_data("test", "test", "invalid", list)
        data = AppData.get_data("test", "test")
        assert data == []


class TestStrType:
    @pytest.mark.django_db
    def test_default_value(self):
        AppData.put_data("test", "test")
        data = AppData.get_data("test", "test")
        assert data == "None"

    @pytest.mark.django_db
    def test_valid_value(self):
        AppData.put_data("test", "test", "test")
        data = AppData.get_data("test", "test")
        assert data == "test"

    @pytest.mark.django_db
    def test_invalid_value(self):
        AppData.put_data("test", "test", 1.5, TestStrType)
        data = AppData.get_data("test", "test")
        assert data == "1.5"


class TestReadAndUpdateMultipleRecords:
    @pytest.mark.django_db
    def test_valid(self):
        AppData.put_data("test.component", "key_1", "abc")
        AppData.put_data("test.component", "key_2", False, bool)
        AppData.put_data("other.component", "key_1", 0, int)

        components = AppData.get_components()
        assert components == {
            "test.component": {
                "key_1": {
                    "id": 1,
                    "data": "abc",
                    "description": "",
                    "type": "str",
                },
                "key_2": {
                    "id": 2,
                    "data": False,
                    "description": "",
                    "type": "bool",
                },
            },
            "other.component": {
                "key_1": {
                    "id": 3,
                    "data": 0,
                    "description": "",
                    "type": "int",
                },
            },
        }

        components = {
            "test.component": {
                "key_2": {
                    "id": 2,
                    "data": True,
                },
            },
            "other.component": {
                "key_1": {
                    "id": 3,
                    "data": 1,
                },
            },
        }

        AppData.post_values(components)
        components = AppData.get_components()
        assert components == {
            "test.component": {
                "key_1": {
                    "id": 1,
                    "data": "abc",
                    "description": "",
                    "type": "str",
                },
                "key_2": {
                    "id": 2,
                    "data": True,
                    "description": "",
                    "type": "bool",
                },
            },
            "other.component": {
                "key_1": {
                    "id": 3,
                    "data": 1,
                    "description": "",
                    "type": "int",
                },
            },
        }
