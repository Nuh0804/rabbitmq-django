from graphene import ObjectType
import graphene
from django.core.paginator import Paginator
from .dtos.Response import ResponseObject, PageObject
from .dtos.MailerDtos import EmailStatusObject, EmailFilteringInputObject, EmailStatusResponseObject
from .models import EmailStatus

from django.db.models import Q



class Query(ObjectType):
    get_emails = graphene.Field(EmailStatusResponseObject,filtering=EmailFilteringInputObject(required=False))


    def resolve_get_emails(self, info, filtering=None, **kwargs):
        try:
            qs = EmailStatus.objects.all()

            if filtering:
                filters = Q()
                if filtering.email_recipient:
                    filters &= Q(email_recipient=filtering.email_recipient)
                if filtering.email_type:
                    filters &= Q(email_type=filtering.email_type)
                if filtering.is_sent is not None:
                    filters &= Q(is_sent=filtering.is_sent)
                if filtering.retries is not None:
                    filters &= Q(retries=filtering.retries)
                qs = qs.filter(filters)

            items_per_page = filtering.items_per_page if filtering and filtering.items_per_page else 10
            page_number = filtering.page_number if filtering and filtering.page_number else 1

            paginated = Paginator(qs, items_per_page)
            required_page = paginated.page(page_number)
            page_object = PageObject.get_page(required_page)

            email_data = [
                EmailStatusObject(
                    id=e.id,
                    unique_id=e.unique_id,
                    email_recipient=e.email_recipient,
                    email_type=e.email_type,
                    email_user=e.email_user,
                    is_sent=e.is_sent,
                    retries=e.retries,
                    email_created_date=e.email_created_date,
                )
                for e in required_page
            ]

            return info.return_type.graphene_type(
                response=ResponseObject.get_response(id="1"),
                data=email_data,
                page=page_object,
            )
        except Exception as e:
            print(e)
            return info.return_type.graphene_type(response=ResponseObject.get_response(id="8"), data=None)
        