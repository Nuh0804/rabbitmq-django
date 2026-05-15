import graphene
from .Response import *

class UserInputObjectType(graphene.InputObjectType):
    first_name = graphene.String()
    last_name = graphene.String()
    username = graphene.String()
    email = graphene.String()


class EmailDataInputObject(graphene.InputObjectType):
    email_type = graphene.String()
    email = graphene.String()
    user = UserInputObjectType()
    request_token = graphene.String()


class EmailStatusObject(graphene.ObjectType):
    id = graphene.Int()
    unique_id = graphene.UUID()
    email_recipient = graphene.String()
    email_type = graphene.String()
    email_user = graphene.String()
    is_sent = graphene.Boolean()
    retries = graphene.Int()
    email_created_date = graphene.Date()

class EmailStatusResponseObject(graphene.ObjectType):
    data = graphene.List(EmailStatusObject)
    response = graphene.Field(ResponseObject)
    page = graphene.Field(PageObject)

class EmailFilteringInputObject(graphene.InputObjectType):
    page_number = graphene.Int()
    items_per_page = graphene.Int()
    is_sent = graphene.Boolean()
    retries = graphene.Int()
    email_recipient = graphene.String()
    email_type = graphene.String()