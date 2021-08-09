from schematics.types import StringType, BooleanType
from openprocurement.tender.openua.procedure.models.bid import (
    Bid as BaseBid,
    PostBid as BasePostBid,
    PatchBid as BasePatchBid,
)
from openprocurement.tender.core.procedure.models.base import ListType
from openprocurement.tender.openeu.procedure.models.lot_value import LotValue, PostLotValue
from openprocurement.tender.openua.procedure.models.document import (
    PostDocument,
    Document,
)
from schematics.types.compound import ModelType


class PatchBid(BasePatchBid):
    lotValues = ListType(ModelType(LotValue, required=True))
    selfQualified = BooleanType(choices=[True])  # selfQualified, selfEligible are the same as in the parent but
    selfEligible = BooleanType(choices=[True])   # tests fail because they in different order
    status = StringType(
        choices=["draft", "pending", "active", "invalid", "invalid.pre-qualification", "unsuccessful", "deleted"],
    )


class PostBid(BasePostBid):
    lotValues = ListType(ModelType(PostLotValue, required=True), default=list)

    documents = ListType(ModelType(PostDocument, required=True), default=list)
    financialDocuments = ListType(ModelType(PostDocument, required=True), default=list)
    eligibilityDocuments = ListType(ModelType(PostDocument, required=True), default=list)
    qualificationDocuments = ListType(ModelType(PostDocument, required=True), default=list)

    selfQualified = BooleanType(required=True, choices=[True])
    selfEligible = BooleanType(choices=[True])
    status = StringType(
        choices=["draft", "pending", "active", "invalid", "invalid.pre-qualification", "unsuccessful", "deleted"]
    )

    _old_default_status = "pending"


class Bid(BaseBid):
    lotValues = ListType(ModelType(LotValue, required=True))

    documents = ListType(ModelType(Document, required=True))
    financialDocuments = ListType(ModelType(Document, required=True))
    eligibilityDocuments = ListType(ModelType(Document, required=True))
    qualificationDocuments = ListType(ModelType(Document, required=True))

    selfQualified = BooleanType(required=True, choices=[True])

    status = StringType(
        choices=["draft", "pending", "active", "invalid", "invalid.pre-qualification", "unsuccessful", "deleted"],
    )