import standards
from schematics.exceptions import ValidationError
from schematics.types import StringType, EmailType

from openprocurement.api.constants import REQUIRED_FIELDS_BY_SUBMISSION_FROM
from openprocurement.api.utils import required_field_from_date
from openprocurement.api.models import (
    ModelType,
    ListType,
    Organization as BaseOrganization,
    Model,
)
from openprocurement.framework.core.procedure.models.address import Address
from openprocurement.framework.core.procedure.models.organization import (
    ContactPoint as BaseContactPoint,
    Identifier,
)
from openprocurement.tender.core.models import PROCURING_ENTITY_KINDS

AUTHORIZED_CPB = standards.load("organizations/authorized_cpb.json")


class ContactPoint(BaseContactPoint):
    email = EmailType(required=True)


class PatchContactPoint(ContactPoint):
    name = StringType()
    email = EmailType()


class ProcuringEntity(BaseOrganization):
    identifier = ModelType(Identifier, required=True)
    additionalIdentifiers = ListType(ModelType(Identifier))
    address = ModelType(Address, required=True)
    contactPoint = ModelType(ContactPoint, required=True)
    kind = StringType(choices=PROCURING_ENTITY_KINDS, default="general")

    def validate_identifier(self, data, identifier):
        pass

    @required_field_from_date(REQUIRED_FIELDS_BY_SUBMISSION_FROM)
    def validate_kind(self, data, value):
        return value


class PatchProcuringEntity(BaseOrganization):
    name = StringType()
    identifier = ModelType(Identifier)
    additionalIdentifiers = ListType(ModelType(Identifier))
    address = ModelType(Address)
    contactPoint = ModelType(PatchContactPoint)
    kind = StringType(choices=PROCURING_ENTITY_KINDS, default="general")

    def validate_identifier(self, data, identifier):
        pass


class PatchActiveProcuringEntity(Model):
    contactPoint = ModelType(PatchContactPoint)
