from core.models import DelegateIntent, DelegateSkill, DelegateUtterance
import json
import pytest


class TestDelegateIntent:

    @pytest.mark.django_db
    def test_serialize(self):
        data = json.dumps({
            'name': 'test',
            'package': 'test',
        })
        skill = DelegateSkill.objects.create(data=data)
        intent = DelegateIntent.objects.create(
            name='test.intent',
            skill_id=skill
        )
        utterances = []
        for i in range(3):
            utterance = DelegateUtterance.objects.create(
                body='Utterance {}'.format(i)
            )
            utterances.append(utterance.id)

        DelegateIntent.post_values(
            'test',
            skill.id,
            utterances[1:],
            intent.id
        )

        expected = {
            'id': intent.id,
            'name': intent.name,
            'skill_id': [
                intent.skill_id.id,
                intent.skill_id.name,
            ],
            'utterance_ids': [
                {'id': 2, 'body': 'Utterance 1'},
                {'id': 3, 'body': 'Utterance 2'},
            ],
        }
        result = intent.serialize()

        assert result == expected

        utterance = DelegateUtterance.objects.first()
        assert utterance.intent_id is None
