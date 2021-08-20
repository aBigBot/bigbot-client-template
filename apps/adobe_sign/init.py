from main.Config import AppConfig
# from apps.adobe_sign.component import AdobeSignAuthProvider, AdobeSignSkill


class Application(AppConfig):

    def init(self, source):
        return super().init(source)

    def registry(self):
        # self.register(AdobeSignAuthProvider)
        # self.register(AdobeSignSkill)

        # self.register_variable("com.big.bot.adobe", "CLIENT_ID", "Adobe Client ID")
        # self.register_variable("com.big.bot.adobe", "CLIENT_SECRET", "Adobe Client SECRET")
        pass
