from openprocurement.api.models import IsoDateTimeType, ValidationError, Value, Period
from openprocurement.tender.core.procedure.models.base import (
    Model, ModelType, ListType, PostBusinessOrganization,
)
from openprocurement.tender.core.procedure.models.document import Document
from openprocurement.tender.core.procedure.context import get_tender, get_now
from schematics.types import StringType, MD5Type, BooleanType, BaseType
from schematics.types.serializable import serializable
from uuid import uuid4


class PostBaseAward(Model):
    @serializable
    def id(self):
        return uuid4().hex

    @serializable
    def date(self):
        return get_now().isoformat()

    qualified = BooleanType()
    status = StringType(required=True, choices=["pending", "active"], default="pending")
    value = ModelType(Value)
    weightedValue = ModelType(Value)
    suppliers = ListType(ModelType(PostBusinessOrganization, required=True), required=True, min_size=1, max_size=1)
    subcontractingDetails = StringType()


class PatchBaseAward(Model):
    qualified = BooleanType()
    status = StringType(choices=["pending", "unsuccessful", "active", "cancelled"])
    title = StringType()
    title_en = StringType()
    title_ru = StringType()
    description = StringType()
    description_en = StringType()
    description_ru = StringType()
    suppliers = ListType(ModelType(PostBusinessOrganization, required=True), min_size=1, max_size=1)
    subcontractingDetails = StringType()
    value = ModelType(Value)


class BaseAward(Model):
    id = MD5Type(required=True, default=lambda: uuid4().hex)
    qualified = BooleanType()
    status = StringType(required=True, choices=["pending", "unsuccessful", "active", "cancelled"])
    date = IsoDateTimeType(required=True)
    value = ModelType(Value)
    weightedValue = ModelType(Value)
    suppliers = ListType(ModelType(PostBusinessOrganization, required=True), required=True, min_size=1, max_size=1)
    documents = ListType(ModelType(Document, required=True))
    subcontractingDetails = StringType()

    title = StringType()
    title_en = StringType()
    title_ru = StringType()
    description = StringType()
    description_en = StringType()
    description_ru = StringType()

    complaints = BaseType()
    complaintPeriod = ModelType(Period)


# Negotiation
def validate_lot_id(value):
    tender = get_tender()
    if not value and tender.get("lots"):
        raise ValidationError("This field is required.")
    if value and value not in tuple(lot["id"] for lot in tender.get("lots", "") if lot):
        raise ValidationError("lotID should be one of lots")


class PostNegotiationAward(PostBaseAward):
    lotID = MD5Type()

    def validate_lotID(self, data, value):
        validate_lot_id(value)


class PatchNegotiationAward(PatchBaseAward):
    lotID = MD5Type()

    def validate_lotID(self, data, value):
        if value:
            validate_lot_id(value)


class NegotiationAward(BaseAward):
    lotID = MD5Type()

    def validate_qualified(self, data, value):
        if not value and data["status"] == "active":
            raise ValidationError("Can't update award to active status with not qualified")


# reporting
class PostReportingAward(PostBaseAward):
    pass


class PatchReportingAward(PatchBaseAward):
    pass


class ReportingAward(BaseAward):
    pass