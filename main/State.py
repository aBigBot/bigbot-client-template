import json

class ChannelState:

    def __init__(self, user_id, operator_id, channel_id, skill, block_id, data, extra, **kwargs):
        self.user_id = user_id
        self.operator_id = operator_id
        self.channel_id = channel_id
        # the two parameter used to determine whether skill is active or not and what is current block state
        self.skill = skill
        self.block_id = block_id
        self.data = data
        self.extra = extra

    # this method used if some skill is active against user and channel
    def is_active(self):
        return True if self.skill else False

    def serialize(self):
        return {
            'user_id':self.user_id,
            'operator_id':self.operator_id,
            'channel_id':self.channel_id,
            'block_id':self.block_id,
            'data':self.data,
            'extra':self.extra,
            'skill':self.skill,
        }

    @staticmethod
    def deserialize(state):
        return ChannelState( state['user_id'],
                            state['operator_id'],
                            state['channel_id'],
                            state['skill'],
                            state['block_id'],
                            state['data'],
                            state['extra'])
