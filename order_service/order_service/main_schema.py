import graphene
from OrderService.views import Mutation 
from OrderService.schema import Query

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    auto_camelcase=True,
)
