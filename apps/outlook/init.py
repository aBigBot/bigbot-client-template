from main.Config import AppConfig
from apps.outlook.component import OutlookOAuthProvider,OutlookCalendarEvent

class Application(AppConfig):

    def init(self, source):
        return super().init(source)

    def registry(self):
        # self.register(OutlookOAuthProvider)
        # self.register(OutlookCalendarEvent)
        pass
