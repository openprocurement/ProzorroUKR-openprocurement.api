from schematics.exceptions import ValidationError
from schematics.types import StringType, BaseType

from openprocurement.api.models import URLType
from openprocurement.api.constants import (
    UA_ROAD_SCHEME,
    UA_ROAD,
    CPV_ITEMS_CLASS_FROM,
    NOT_REQUIRED_ADDITIONAL_CLASSIFICATION_FROM,
    ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017,
    ADDITIONAL_CLASSIFICATIONS_SCHEMES,
    CPV_CODES,
    DK_CODES,
    CPV_BLOCK_FROM,
    GMDN_2019_SCHEME,
    GMDN_2019,
    GMDN_2023_SCHEME,
    GMDN_2023,
)
from openprocurement.api.models import Model
from openprocurement.api.procedure.utils import is_obj_const_active


class Classification(Model):
    scheme = StringType(required=True)  # The classification scheme for the goods
    id = StringType(required=True)  # The classification ID from the Scheme used
    description = StringType(required=True)  # A description of the goods, services to be provided.
    description_en = StringType()
    description_ru = StringType()
    uri = URLType()


class CPVClassification(Classification):
    scheme = StringType(required=True, default="CPV", choices=["CPV", "ДК021"])
    id = StringType(required=True)

    def validate_id(self, data, code):
        if data.get("scheme") == "CPV" and code not in CPV_CODES:
            raise ValidationError("Value must be one of CPV codes")
        elif data.get("scheme") == "ДК021" and code not in DK_CODES:
            raise ValidationError("Value must be one of ДК021 codes")


class AdditionalClassification(Classification):
    def validate_id(self, data, value):
        if data["scheme"] == UA_ROAD_SCHEME and value not in UA_ROAD:
            raise ValidationError(f"{UA_ROAD_SCHEME} id not found in standards")
        if data["scheme"] == GMDN_2019_SCHEME and value not in GMDN_2019:
            raise ValidationError(f"{GMDN_2019_SCHEME} id not found in standards")
        if data["scheme"] == GMDN_2023_SCHEME and value not in GMDN_2023:
            raise ValidationError(f"{GMDN_2023_SCHEME} id not found in standards")

    def validate_description(self, data, value):
        if data["scheme"] == UA_ROAD_SCHEME and UA_ROAD.get(data["id"]) != value:
            raise ValidationError("{} description invalid".format(UA_ROAD_SCHEME))


def validate_scheme(obj, scheme):
    if scheme != "ДК021" and is_obj_const_active(obj, CPV_BLOCK_FROM):
        raise ValidationError(BaseType.MESSAGES["choices"].format(["ДК021"]))


def validate_additional_classifications(obj, data, items):
    obj_from_2017 = is_obj_const_active(obj, CPV_ITEMS_CLASS_FROM)
    not_cpv = data["classification"]["id"] == "99999999-9"
    if (
        not items and (
            not obj_from_2017
            or obj_from_2017
            and not_cpv
            and not is_obj_const_active(obj, NOT_REQUIRED_ADDITIONAL_CLASSIFICATION_FROM)
        )
    ):
        raise ValidationError("This field is required.")
    elif (
        obj_from_2017
        and not_cpv
        and items
        and not any(i.scheme in ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017 for i in items)
    ):
        raise ValidationError(
            "One of additional classifications should be one of [{0}].".format(
                ", ".join(ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017)
            )
        )
    elif (
        not obj_from_2017
        and items
        and not any(i.scheme in ADDITIONAL_CLASSIFICATIONS_SCHEMES for i in items)
    ):
        raise ValidationError(
            "One of additional classifications should be one of [{0}].".format(
                ", ".join(ADDITIONAL_CLASSIFICATIONS_SCHEMES)
            )
        )


def validate_items_uniq(items, *args):
    if items:
        ids = [i.id for i in items]
        if len(ids) > len(set(ids)):
            raise ValidationError("Item id should be uniq for all items")


def validate_cpv_group(items, *args):
    if items:
        if (
            items[0].classification.id[:3] != "336"
            and len({i.classification.id[:4] for i in items}) != 1
        ):
            raise ValidationError("CPV class of items should be identical")
