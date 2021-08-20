import uuid
from django.db.models.signals import post_save, pre_save
from .models import MailService

def pre_save_mail_service(sender, instance, **kwargs):
    pass

def post_save_mail_service(sender, instance, created, **kwargs):

    from_email = instance.email_from
    subject = instance.subject
    html_content = instance.content
    provider = instance.provider
    to_emails = []
    for recipient in instance.recipients.all():
        to_emails.append(recipient.email)
    MailService.send(from_email,subject,to_emails,html_content,provider)

pre_save.connect(pre_save_mail_service, sender=MailService)
post_save.connect(post_save_mail_service, sender=MailService)
