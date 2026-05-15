import json
from typing import Any, Callable

from django.core.paginator import Paginator, Page
from django.db.models import Model, Q

import graphene


class PageObject(graphene.ObjectType):
    number = graphene.Int()
    has_next_page = graphene.Boolean()
    has_previous_page = graphene.Boolean()
    next_page_number = graphene.Int()
    previous_page_number = graphene.Int()
    number_of_pages = graphene.Int()
    total_items = graphene.Int()
    pages = graphene.List(graphene.Int)

    @staticmethod
    def get_page(page_object):

        previous_page_number = 0
        next_page_number = 0

        if page_object.number > 1:
            previous_page_number = page_object.previous_page_number()

        try:
            next_page_number = page_object.next_page_number()
        except:
            next_page_number + page_object.number

        return PageObject(
            number=page_object.number,
            has_next_page=page_object.has_next(),
            has_previous_page=page_object.has_previous(),
            next_page_number=next_page_number,
            previous_page_number=previous_page_number,
            number_of_pages = page_object.paginator.num_pages,
            total_items = page_object.paginator.count,
            pages = page_object.paginator.page_range
        )


class ResponseObject(graphene.ObjectType):
    id = graphene.String()
    status = graphene.Boolean()
    code = graphene.Int()
    message = graphene.String()

    @staticmethod
    def __read_code_file(code_id):
        file = open('response_codes.json', 'r')
        file_codes = file.read()
        response_codes = json.loads(file_codes)
        response_code = next(code for code in response_codes if code["id"] == code_id)
        return response_code

    @staticmethod
    def get_response(id):
        try:

            response_code = ResponseObject.__read_code_file(id)
            return ResponseObject(
                response_code['id'],
                response_code['status'],
                response_code['code'],
                response_code['message'],
            )
        except:
            return ResponseObject()


def get_data(model_class, filter_field, id, graphene_object_class, child_model_class=None, child_graphene_object_class=None):
    # TODO: Create a helper function as builder function
    """Provides a generic method to retrieve data from a model and create a corresponding GraphQL object.

    Args:
        model_class (django.db.models.Model): The Django model class representing the data.
        queryset_method (function): A method on the model instance that returns a queryset for related objects.
        filter_field (str): The field name to use for filtering based on the `id` parameter.
        id (str|int|None): The ID value to use for filtering.
        graphene_object_class (graphene.ObjectType): The Graphene object class responsible for representing the data in GraphQL.
        child_queryset_method (function, optional): A method on the model instance that returns a queryset for nested child objects.
        child_graphene_object_class (graphene.ObjectType, optional): The Graphene object class for representing nested child objects.

    Returns:
        graphene.ObjectType: An instance of the provided `graphene_object_class`, populated with data from the model and any nested child objects.

    Raises:
        ValueError: If either `model_class` or `graphene_object_class` is not provided.
        
    Example usage:
        institution_data = CommonBuilder.get_data(
            Institution, Institution.get_departments, 'institution_unique_id', id, InstitutionObject
        )
    """
    if child_graphene_object_class and not child_model_class:
        raise ValueError("child_graphene_object_class is provided but child_model_class is missing.")

    if id is not None:
        print(id)
        
        obj = model_class.objects.filter(institution_unique_id=id).first()

        if obj:
            child_list = None
            if child_model_class:
                child_data = child_model_class.objects.filter(**{f"{filter_field}_{model_class.__name__.lower()}": obj.id})
                child_list = list(map(lambda x: get_data(child_model_class, f"{filter_field}_{model_class.__name__.lower()}", x.id, child_graphene_object_class), child_data,))
                
            return graphene_object_class(
                id=obj.primary_key,
                **{field: getattr(obj, field) for field in graphene_object_class._meta.fields},
                **{child_model_class.__name__.lower(): child_list} if child_list else {},
            )
        else:
            return graphene_object_class()
    else:
        return graphene_object_class()

def test_get_paginated_data(model:Model, filters:Q, page_number:int, graphene_object_class, items_per_page:int=None, lookup:str="unique_id") -> tuple[ResponseObject, Page, list[Any]]:
    """
    Fetches, paginates, and builds data for a given model class.

    Args:
        model (Model): The Django model to query.
        filters (Q): The filters to apply to the queryset.
        page_number (int): The desired page number.
        builder_function (function): A function that takes a model object's lookup(str) and returns its data.
        items_per_page (int): Number of items per page, default is 20.
        lookup (str): The field to select in the queryset.

    Returns:
        tuple: A tuple containing the response, page, data.
    """

    queryset = model.objects.filter(filters).only(lookup)
    paginated_data = Paginator(queryset, items_per_page if items_per_page else 20)
    page_obj = paginated_data.page(page_number)
    data = [get_data(model, filters, getattr(obj, lookup), graphene_object_class) for obj in page_obj]
    page = PageObject.get_page(paginated_data.page(page_number))
    return ResponseObject.get_response(id="1"), page, data

def get_paginated_data(model:Model, filters:Q, page_number:int, builder_function:Callable[[str], Any], items_per_page:int=None, lookup:str="unique_id") -> tuple[ResponseObject, Page, list[Any]]:
    """
    Fetches, paginates, and builds data for a given model class.

    Args:
        model (Model): The Django model to query.
        filters (Q): The filters to apply to the queryset.
        page_number (int): The desired page number.
        builder_function (function): A function that takes a model object's lookup(str) and returns its data.
        items_per_page (int): Number of items per page, default is 20.
        lookup (str): The field to select in the queryset.

    Returns:
        tuple: A tuple containing the response, page, data.
    """

    queryset = model.objects.filter(filters).only(lookup)
    paginated_data = Paginator(queryset, items_per_page if items_per_page else 20)
    page_obj = paginated_data.page(page_number)
    data = [builder_function(getattr(obj, lookup)) for obj in page_obj]
    page = PageObject.get_page(paginated_data.page(page_number))
    return ResponseObject.get_response(id="1"), page, data