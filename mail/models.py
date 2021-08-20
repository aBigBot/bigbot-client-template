from django.db import models
from core.models import User,Preference
from django.template.loader import get_template
from django.template import Context, Template
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail,To
from django.conf import settings

class MailService(models.Model):
    content = models.TextField()
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sender',null=True)
    date = models.DateTimeField(auto_now=True)
    recipients = models.ManyToManyField(User, related_name='recipients')
    email_from = models.EmailField(max_length=100,blank=True)
    subject = models.CharField(max_length=200)
    provider = models.CharField(max_length=200,default='sendgrid')

    def __str__(self):
        return self.subject

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.email_from:
                self.email_from = self.sender.email
        super(MailService, self).save(*args, **kwargs)

    @staticmethod
    def simple_send(subject, content, recipient):
        email_from = 'no-reply@abigbot.com'
        record = MailService.objects.create(subject=subject, content=content,email_from=email_from)
        record.recipients.add(recipient)
        record.save()

    @staticmethod
    def send(from_email, subject, recipients_emails, content, provider = 'sendgrid'):
        if recipients_emails:
            if provider == 'sendgrid':
                to_emails = []
                for recipients_email in recipients_emails:
                    to_emails.append(To(recipients_email))
                message = Mail(
                    from_email=from_email,
                    to_emails=to_emails,
                    subject=subject,
                    html_content=content)

                try:
                    SENDGRID_APIKEY = Preference.get_value('SENDGRID_APIKEY')
                    if SENDGRID_APIKEY:
                        import os, ssl
                        if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
                                getattr(ssl, '_create_unverified_context', None)):
                            ssl._create_default_https_context = ssl._create_unverified_context
                        sg = SendGridAPIClient(SENDGRID_APIKEY)
                        response = sg.send(message)
                except Exception as e:
                    print(e)




