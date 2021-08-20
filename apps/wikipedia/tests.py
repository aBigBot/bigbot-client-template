import pytest
from component import GetRandomPageIntent, SearchIntent
from init import Application
from main.Intent import ProcessText
import spacy

nlp = spacy.load('en_core_web_sm')


inputs = [
    # (input, expected intent)
    ("Show me a random page", GetRandomPageIntent),
    ("show me anything", GetRandomPageIntent),
    ("What is a noun", SearchIntent),
    ("Could you please find who is Sachin Tendulakar", SearchIntent),
    ("Who is Rafael Nadal", SearchIntent),
    ("What is the capital of Srilanka", SearchIntent),
    ("Search apple fruit", SearchIntent),
    ("Search an Apple", SearchIntent),
    ("Find out the largest number", SearchIntent),
    ("What is an orange and an apple", SearchIntent),
    ("Search a Lion. Also Search for a tiger", SearchIntent),
    ("How many players are there in a cricket team", SearchIntent),
    ("Search how many players are there in a cricket team", SearchIntent),
    ("Who is the captain of England Cricket Team", SearchIntent),
    ("What is a Kite. What is a cheetah. Who is Nikola Tesla", SearchIntent),
]


class TestIntegration:
    def test_matching(self):
        app = Application()
        result = []
        
        # Code similar to this loop will be used to process the intents
        for input, expected_component in inputs:
            matches = []
            my_processed_text = ProcessText(input,nlp)
            for intent, component, kwargs in app.intents:
                data = intent.match(my_processed_text,input)
                matches.append((data,intent))
            for i in range(len(matches)):
                if matches[i][0] != 0:
                    result.append(matches[i])
        return result