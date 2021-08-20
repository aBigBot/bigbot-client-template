import pytest

from core.models import AppData
from contrib.application import AppConfig
from main.Component import BaseComponent


class TestRegisterVariable:
    @pytest.mark.django_db
    def test_register_variable(self):
        class MockApplication(AppConfig):
            def init(self, source):
                self.registry()

            def registry(self):
                self.register_variable("test.component", "my_test_variable", "description")

        app = MockApplication("test")

        record = AppData.objects.first()
        assert record.key == "my_test_variable"
        assert record.data == "None"

    @pytest.mark.django_db
    def test_register_variable_with_type(self):
        class MockApplication(AppConfig):
            def init(self, source):
                self.registry()

            def registry(self):
                self.register_variable("test.component", "my_test_variable", "description", bool)

        app = MockApplication("test")

        record = AppData.objects.first()
        assert record.key == "my_test_variable"
        assert record.data == "False"

    @pytest.mark.django_db
    def test_register_variable_with_value(self):
        class MockApplication(AppConfig):
            def init(self, source):
                self.registry()

            def registry(self):
                self.register_variable(
                    "test.component", "my_test_variable", "description", bool, True
                )

        app = MockApplication("test")

        record = AppData.objects.first()
        assert record.key == "my_test_variable"
        assert record.data == "True"

    @pytest.mark.django_db
    def test_get_variable(self):
        class MockApplication(AppConfig):
            def init(self, source):
                self.registry()

            def registry(self):
                self.register_variable(
                    "test.component", "my_test_variable", "description", list, [1, 2, 3]
                )

        class MockComponent(BaseComponent):
            pass

        app = MockApplication("test")
        component = MockComponent(None)

        variable = component.get_variable("test.component", "my_test_variable")

        assert variable == [1, 2, 3]
