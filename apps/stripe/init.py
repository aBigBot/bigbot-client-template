from main.Config import AppConfig
from apps.stripe.component import StripeCheckout

class Application(AppConfig):

    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(StripeCheckout)
