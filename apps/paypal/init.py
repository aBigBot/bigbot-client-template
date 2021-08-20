from main.Config import AppConfig
from apps.paypal.component import PayPalCheckout


class Application(AppConfig):
    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(PayPalCheckout)

        self.register_variable("com.big.bot.paypal", "CLIENT_ID", "Paypal Client ID")
        self.register_variable("com.big.bot.paypal", "CLIENT_SECRET", "Paypal Client SECRET")
