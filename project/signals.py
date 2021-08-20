# import django.dispatch
# typing_status = django.dispatch.Signal(providing_args=["user","data"])
#
# @receiver(typing_status)
# def on_typing_status_changed(sender, user, data,  **kwargs):
#     print('typing...........')
#     print(str(user))
#     print(data['text'])
#     pass
#
# typing_status.send(sender=WebSocketConsumer, user=user, data=data)