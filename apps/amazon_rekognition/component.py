import base64
import boto3
import io
import requests
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from main.Component import DataExchange, SkillProvider
from main.Statement import OutputStatement


class ImageRecognition:
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, aws_region: str):
        self.AWS_ACCESS_KEY_ID = aws_access_key_id
        self.AWS_SECRET_ACCESS_KEY = aws_secret_access_key
        self.AWS_REGION = aws_region
        self.client = boto3.client(
            "rekognition",
            aws_access_key_id=self.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
            region_name=self.AWS_REGION,
        )

    def get_labels(self, image: bytes, max_label: int, base_confidence_level: int):
        labels = {}

        response = self.client.detect_labels(Image={"Bytes": image}, MaxLabels=max_label)

        for label in response["Labels"]:
            if label["Confidence"] > base_confidence_level:
                labels.update({label["Name"]: len(label["Instances"])})
        return labels

    def format_labels(self, image: bytes, max_label: int, base_confidence_level: int):
        labels = self.get_labels(image, max_label, base_confidence_level)
        labels_str = ""
        if len(labels.keys()) == 0:
            labels_str = "none"
        else:
            for label, count in labels.items():
                if len(labels_str) > 0:
                    labels_str += ", "
                if count > 0:
                    labels_str += "{} {}".format(count, label)
                else:
                    labels_str += str(label)
        return "Image may contain: " + labels_str


class ImageRecognitionSkillProvider(SkillProvider):
    def __init__(self, config):
        access_key = self.get_variable("com.big.bot.amazon.aws", "AWS_ACCESS_KEY_ID")
        region = self.get_variable("com.big.bot.amazon.aws", "AWS_REGION")
        secret_key = self.get_variable("com.big.bot.amazon.aws", "AWS_SECRET_ACCESS_KEY")
        self.recognition = ImageRecognition(access_key, secret_key, region)
        super().__init__(config)

    def extract_image(self, file):
        if isinstance(file, str):
            validator = URLValidator()
            try:
                validator(file)
                return self.img_to_base64_bytes(file)
            except ValidationError as e:
                return ""
        elif isinstance(file, dict):
            base64_string = file.get("file").split(",")[-1]
            return base64.b64decode(base64_string)

    def img_to_base64_bytes(self, img_url: str) -> str:
        r = requests.get(img_url)
        # TODO: check response is an image or not
        with io.BytesIO() as buf:
            buf.write(r.content)
            buf.seek(0)
            buf_bytes = buf.read()

            base64_img = base64.b64encode(buf_bytes)
            return base64.decodebytes(base64_img)

    def on_execute(self, binder, user_id, package, data, **kwargs):
        image = self.extract_image(data.get("img"))
        result = (
            self.recognition.format_labels(image, 10, 90)
            if image
            else "Please use a valid image or url."
        )

        output = OutputStatement(user_id)
        output.append_text(result)
        binder.post_message(output)

    def on_search(self, binder, user_id, package, data, query, **kwargs):
        pass


class RecognizeImage(DataExchange):
    def __init__(self, config):
        access_key = self.get_variable("com.big.bot.amazon.aws", "AWS_ACCESS_KEY_ID")
        region = self.get_variable("com.big.bot.amazon.aws", "AWS_REGION")
        secret_key = self.get_variable("com.big.bot.amazon.aws", "AWS_SECRET_ACCESS_KEY")
        self.recognition = ImageRecognition(access_key, secret_key, region)
        super().__init__(config)

    def call(self, binder, operator_id, package, data, **kwargs):
        image = self.extract_image(kwargs.get("input_image"))
        result = (
            self.recognition.format_labels(image, 10, 90)
            if image
            else "Please use a valid image or url."
        )

        output = OutputStatement(operator_id)
        output.append_text(result)
        binder.post_message(output)

        result = list(map(lambda x: x.strip().lower(), result.split(":")[1].split(",")))

        return {"result": result}

    def extract_image(self, file):
        if isinstance(file, str):
            validator = URLValidator()
            try:
                validator(file)
                return self.img_to_base64_bytes(file)
            except ValidationError as e:
                return ""
        elif isinstance(file, dict):
            base64_string = file.get("file").split(",")[-1]
            return base64.b64decode(base64_string)

    def img_to_base64_bytes(self, img_url: str) -> str:
        r = requests.get(img_url)
        # TODO: check response is an image or not
        with io.BytesIO() as buf:
            buf.write(r.content)
            buf.seek(0)
            buf_bytes = buf.read()

            base64_img = base64.b64encode(buf_bytes)
            return base64.decodebytes(base64_img)
