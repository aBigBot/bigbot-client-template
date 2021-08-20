import json
import textdistance
from . import Log


class UtteranceDistance:

    def __init__(self, utterances, query, **kwargs):
        self.algorithm = kwargs.get('algorithm', 'levenshtein')
        self.utterances  = utterances
        self.query = query
        self.distance = 0.0
        self.index = None
        self.text = None
        if self.query:
           self._compute(query)

    def _compute(self, input):
        index = 0
        for utterance in self.utterances:
            if type(utterance) != str or type(input) != str:
                continue
            match_distance = textdistance.levenshtein.normalized_similarity(
                input.lower(),
                utterance.lower(),
            )
            if match_distance > self.distance:
                self.distance = match_distance
                self.text = utterance
                self.index = index
            index = index+1


    def __str__(self):
        return "'{}', index:{}, confidence: {}%".format(self.text,str(self.index),str(self.get_confidence()))

    def get_text(self):
        return self.text

    def get_distance(self):
        return self.distance

    def get_confidence(self):
        return int(self.distance*100)

    def get_index(self):
        return self.index
