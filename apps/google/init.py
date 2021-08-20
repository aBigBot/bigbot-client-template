from main.Config import AppConfig
from apps.google.component import GoogleOAuthProvider,GoogleCalendarEvent,UserCalendarEvent
# from apps.google.component import GoogleScheduleAppointment
# from apps.google.component import EmptyProvider
# from apps.google.component import ScheduleAppointment
from apps.google.component import RouteForScheduleProvider

class Application(AppConfig):

    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(GoogleOAuthProvider)
        # self.register(GoogleCalendarEvent)
        # self.register(UserCalendarEvent)
        # self.register(GoogleScheduleAppointment)
        # self.register(EmptyProvider)
        # self.register(ScheduleAppointment)
        self.register(RouteForScheduleProvider)

        self.register_variable("com.big.bot.google", "CLIENT_ID", "Google Client ID")
        self.register_variable("com.big.bot.google", "CLIENT_SECRET", "Google Client SECRET")
        self.register_variable("com.big.bot.google", "API_KEY", "Google API key")
        self.register_variable(
            "com.big.bot.google", "ORIGIN_COUNTRY", "Country to be used with Google Maps"
        )
        # pass
