import json

class Statement:
    """
    A statement represents a single spoken entity, sentence or
    phrase that someone can say.
    """

    __slots__ = (
        'text',
        'contents',
        'confidence',
        'tags',
        'uid'
    )

    def __init__(self, text, uid, **kwargs):

        self.text = text
        self.uid = uid
        self.tags = kwargs.get('tags',{})
        self.contents = kwargs.get('contents',[])
        self.confidence = kwargs.get('confidence', 0)
        self.process_tts()

    def __str__(self):
        return str(self.text)

    def save(self):
        """
        Save the statement in the database.
        """
        pass

    def get_tag(self, name):
        """
        Return the tag from it's name.
        """
        return self.tags[name] if name in self.tags else False

    def add_tag(self, name, object):
        """
        Add a list of strings to the statement as tags.
        """
        self.tags[name] = object

    def process_tts(self):
        """
        Adds a TTS node to contents
        """
        from core.models import TTSAudio
        from contrib.utils import get_full_url
        from django.urls import reverse

        string = None

        if len(self.contents) == 0:
            string = self.text
        else:
            for node in self.contents:
                if type(node) == dict and  'node' in node:
                    if node['node'] == 'big.bot.core.text':
                        string = node['data']

        if string is not None:
            try:
                tts_uuid = TTSAudio.generate_reference(string, True)
                self.contents.append({
                    'data': get_full_url('{}?uuid={}'.format(
                        reverse('tts_audio'),
                        tts_uuid
                    )),
                    'node': 'big.bot.core.tts'
                })
            except Exception as e:
                print('===== Error Processing TTS =====')
                print(e)

    def serialize(self):
        """
        :returns: A dictionary representation of the statement object.
        :rtype: dict
        """
        data = {
            'text':self.text,
            'confidence':self.confidence,
            'contents':self.contents,
            'tags':self.tags,
            'uid':self.uid,
        }
        return data
