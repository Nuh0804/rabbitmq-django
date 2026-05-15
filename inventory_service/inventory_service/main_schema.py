import graphene
from InventoryService.views import Mutation 
from InventoryService.schema import Query

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    auto_camelcase=True,
)
