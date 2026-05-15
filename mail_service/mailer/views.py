from django.shortcuts import render
import graphene
from dotenv import dotenv_values
from .dtos.Response import ResponseObject
from .EmailService import CustomEmailBackend
from .models import EmailStatus
from .dtos.MailerDtos import *


config = dotenv_values(".env")

# Create your views here.
EMAIL_TEMPLATES = {
    "ACCOUNT_CREATED": {
        "subject": "my site Activate Account",
        "template_path": "htmls/create_password.html",
        "url_path": "/auth/setPwd/"
    },
    "PASSWORD_RESET": {
        "subject": "my site Password Reset",
        "template_path": "htmls/forget_password.html",
        "url_path": "auth/password-reset/"
    },
}


class SendEmailMutation(graphene.Mutation):
    class Arguments:
        input = EmailDataInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data = graphene.String()

    def mutate(cls, root, info,  input):
        email_type = input.email_type
        if email_type is None:
            return cls(response=ResponseObject.get_response(id="10"), data=None)
        
        if email_type not in EMAIL_TEMPLATES:
            return cls(response=ResponseObject.get_response(id="5"), data=None)
        
        email_context = EMAIL_TEMPLATES[email_type]
        email_status = EmailStatus.Objects.create(
                email_recipient = input.email,
                email_type = input.email_type,
                email_user = input.user,
                is_sent = False,
                retries = 0,
        )
        url = config['FRONTEND_DOMAIN'] + f"{email_context.url_path}"
        body = {
            'receiver_details': input.email,
            'user': input.user,
            'url': url,
            'subject': {email_context.subject}
        }        
        try:
            CustomEmailBackend.send_messages(body, email_context.template_path)
            email_status.is_sent = True
            email_status.save
            return cls(response=ResponseObject.get_response(id="1"), data="Email Sent")
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class Mutation(graphene.ObjectType):
    send_email_mutation = SendEmailMutation.Field()
