from chatterbot.logic import LogicAdapter
from chatterbot.comparisons import levenshtein_distance
from chatterbot.conversation import Statement
import random
from .models import InputPattern, ResponsePhrase

class CorpusAdapter(LogicAdapter):

    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        self.delegate = kwargs.get('delegate')

    def can_process(self, statement):
        return True

    def process(self, input_statement, additional_response_selection_parameters, **kwargs):
        threshold = 0
        input_text = input_statement.text

        patterns = InputPattern.objects.filter(delegate_id=self.delegate.id) if self.delegate else InputPattern.objects.all()
        distance = []
        for pattern in patterns:
            distance.append(levenshtein_distance.compare(Statement(pattern.string), Statement(input_text)))

        if distance:
            best_match_index = distance.index(max(distance))
            confidence = max(distance)
            if distance[best_match_index] >= threshold:
                phrases = []
                for phrase in  patterns[best_match_index].response_ids.all():
                    phrases.append(phrase.string)
                selected_statement = Statement(text=random.choice(phrases))
                selected_statement.confidence = confidence
                return selected_statement

        return input_statement
