from main.Config import AppConfig
from apps.bigbot.component import (
    BigbotCorpus,
    BigbotMathematical,
    BigbotUnitConversion,
    BigbotUtterances,
)


class Application(AppConfig):
    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(BigbotCorpus)
        self.register(BigbotMathematical)
        self.register(BigbotUnitConversion)
        self.register(BigbotUtterances)
