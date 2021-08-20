import spacy
from spacy.matcher import Matcher
from spacy.tokens import Token
import typing

class ProcessText:
    
    def __init__(self, input_statement, nlp):
        self.nlp = nlp
        self.doc = nlp(input_statement)
        self.names = None
        self.ORGs = None
        self.GPEs = None
        self.dates = None
        self.times = None
        self.moneys = None
        #self.matcher = Matcher(self.nlp.vocab)


    def get_is_match(self, pattern):
        """This method matches the pattern with the input
            arguments : pattern

            returns :  + is_matched (boolean) - if patterns matched returns True
                       + span_tokens (list) - list of span tokens - list(tokens matched)
                       + doc - spacy doc object that'll be used in filtering span tokens in Intent.on_match() method
        """
        self.pattern = pattern
        self.is_matched = False
        self.matcher = Matcher(self.nlp.vocab)
        self.matcher.add('pattern_name', [self.pattern])
        self.matches = self.matcher(self.doc)
        self.span = []
        self.span_tokens = []
        for match_id,start,end in self.matches:
            self.match_type = self.nlp.vocab.strings[match_id]
            self.span.append(self.doc[start:end])
            
        if len(self.span) > 0:
            self.is_matched = True
            self.all_spans = [[j for j in i] for i in self.span]
            #self.span_tokens = [k[idx] for idx in range(len(k)) for k in self.all_spans]
            for k in self.all_spans:
                for idx in range(len(k)):
                    self.span_tokens.append(k[idx])
            return self.is_matched,self.span_tokens,self.doc
        
        else:
            return self.is_matched,None,None




class Intent:
    def __init__(self, patterns: typing.List[str] = []):
        self.pat = patterns

    def match(self,processed_text, input: str) -> int:
        """Checks if input matches a pattern.

        Arguments:
            + processed_text - a ProcessText object
            + input - input string

        Retruns:
            [list|None]:
                + returns a list of extracted data from input list(str), if no match is found
                returns None
        """
        # Use spacy Match

        for pat in self.pat:
            #print(pat)
            self.is_match,self.tokens_matched,self.input_text_to_doc = processed_text.get_is_match(pattern = pat)
            #print(self.is_match)
            
            if self.is_match:
                return self.on_match(self.input_text_to_doc)
            else:
                return 0

    def get_is_excluded(self,token):
        """This is the getter method used by spacy Token.set_extension()
           + tokens_matched is the list of span tokens returned by ProcessText.get_is_match()
        """
        return token.text in [i.text for i in self.tokens_matched]
        


    def on_match(self,input_doc):
        """Extracts found data from match.

        Args:
            input (doc): doc object of input string

        Returns:
            str: extracted data from the original input
        """
        # Rewrite function to work as the on_match parameter in the method Matcher.add
        
        Token.set_extension('is_excluded', getter = self.get_is_excluded, force = True)
        self.extracted_data = [token.text for token in input_doc if token.pos_ not in ['ADP','DET','PUNCT','CCONJ'] and not token._.is_excluded]
        
        if len(self.extracted_data)>0:
            return self.extracted_data
        else:
            return 0
