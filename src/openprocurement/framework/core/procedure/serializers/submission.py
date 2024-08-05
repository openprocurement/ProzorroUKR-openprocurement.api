from openprocurement.api.procedure.serializers.base import (
    BaseUIDSerializer,
    ListSerializer,
)
from openprocurement.api.procedure.serializers.config import BaseConfigSerializer
from openprocurement.framework.core.procedure.serializers.document import (
    SubmissionDocumentSerializer,
)


class SubmissionSerializer(BaseUIDSerializer):
    base_private_fields = {
        "transfer_token",
        "_rev",
        "doc_type",
        "rev",
        "revisions",
        "public_modified",
        "is_public",
        "is_test",
        "config",
        "__parent__",
        "_attachments",
        "dateCreated",
        "owner_token",
        "framework_owner",
        "framework_token",
    }
    serializers = {
        "documents": ListSerializer(SubmissionDocumentSerializer),
    }

    def __init__(self, data: dict):
        super().__init__(data)
        self.private_fields = set(self.base_private_fields)


def test_serializer(obj, value):
    if value is False:
        return None
    return value


def restricted_serializer(obj, value):
    if value is None:
        return False
    return value


class SubmissionConfigSerializer(BaseConfigSerializer):
    serializers = {
        "test": test_serializer,
        "restricted": restricted_serializer,
    }
