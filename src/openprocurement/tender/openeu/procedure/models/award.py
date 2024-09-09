from schematics.types import BaseType, BooleanType
from schematics.types.compound import ModelType

from openprocurement.api.procedure.types import ListType
from openprocurement.tender.core.procedure.models.award import Award as BaseAward
from openprocurement.tender.core.procedure.models.award import (
    PatchAward as BasePatchAward,
)
from openprocurement.tender.core.procedure.models.award import (
    PostAward as BasePostAward,
)
from openprocurement.tender.core.procedure.models.guarantee import WeightedValue
from openprocurement.tender.openua.procedure.models.item import Item


class Award(BaseAward):
    complaints = BaseType()
    items = ListType(ModelType(Item, required=True))
    eligible = BooleanType()
    weightedValue = ModelType(WeightedValue)


class PatchAward(BasePatchAward):
    items = ListType(ModelType(Item, required=True))
    eligible = BooleanType()


class PostAward(BasePostAward):
    weightedValue = ModelType(WeightedValue)
