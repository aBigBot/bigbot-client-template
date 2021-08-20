from main.Config import AppConfig
from apps.amazon_rekognition.component import ImageRecognitionSkillProvider, RecognizeImage


class Application(AppConfig):
    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(ImageRecognitionSkillProvider)
        self.register_data_exchange(
            RecognizeImage,
            "Recognize Image",
            "Use ML to identify the elements in the image",
            input=[
                {
                    "description": "Input Image",
                    "name": "input_image",
                    "readable": "Input Image",
                    "type": "url",
                },
            ],
            output=[
                {
                    "description": "Description of the elements in the image",
                    "name": "result",
                    "readable": "Image Description",
                    "type": "str",
                }
            ],
        )
        self.register_variable(
            "com.big.bot.amazon.aws", "AWS_ACCESS_KEY_ID", "Your AWS access key id"
        )
        self.register_variable(
            "com.big.bot.amazon.aws",
            "AWS_REGION",
            "Preferred AWS Rregion",
        )
        self.register_variable(
            "com.big.bot.amazon.aws", "AWS_SECRET_ACCESS_KEY", "Your AWS secret access key"
        )
