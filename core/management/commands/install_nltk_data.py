import subprocess

from django.core.management.base import BaseCommand, CommandError
import nltk


class Command(BaseCommand):
    help = "Installs required NLTK data"

    def handle(self, *args, **options):
        # Required by app.bigbot.component.BigbotUnitConversion
        nltk.download("punkt")
        # Required by app.bigbot.component.BigbotMathematical
        nltk.download("stopwords")
        # Installs spacy model
        subprocess.call(["python", "-m", "spacy", "download", "en_core_web_md"])
