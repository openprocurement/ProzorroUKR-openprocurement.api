from openprocurement.api.procedure.serializers.base import BaseSerializer


class RequirementSerializer(BaseSerializer):
    pass


class PutCancelledRequirementSerializer(RequirementSerializer):
    whitelist = [
        "id",
        "status",
        "datePublished",
        "dateModified",
    ]
