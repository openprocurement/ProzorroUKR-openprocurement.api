from datetime import timedelta

from openprocurement.api.utils import raise_operation_error, get_now
from openprocurement.api.validation import OPERATIONS
from openprocurement.framework.core.validation import validate_framework_patch_status
from openprocurement.framework.electroniccatalogue.utils import calculate_framework_date

MIN_QUALIFICATION_DURATION = 30
MAX_QUALIFICATION_DURATION = 1095


def validate_qualification_period_duration(request, model):
    data = request.validated["data"]
    period = model(request.validated["data"]["qualificationPeriod"])
    qualification_period_end_date = calculate_framework_date(period.startDate,
                                                             timedelta(days=MIN_QUALIFICATION_DURATION), data)
    if qualification_period_end_date > period.endDate:
        raise_operation_error(request,
                              u"qualificationPeriod must be at least {min_duration} full calendar days long".format(
                                  min_duration=MIN_QUALIFICATION_DURATION))
    qualification_period_end_date = calculate_framework_date(period.startDate,
                                                             timedelta(days=MAX_QUALIFICATION_DURATION), data)
    if qualification_period_end_date < period.endDate:
        raise_operation_error(request,
                              u"qualificationPeriod must be less than {max_duration} full calendar days long".format(
                                  max_duration=MAX_QUALIFICATION_DURATION))


def validate_ec_framework_patch_status(request):
    allowed_statuses = ("draft", "active")
    validate_framework_patch_status(request, allowed_statuses)


def validate_framework_document_operation_not_in_allowed_status(request):
    if request.validated["framework"].status not in ["draft", "active"]:
        raise_operation_error(
            request,
            "Can't {} document in current ({}) contract status".format(
                OPERATIONS.get(request.method), request.validated["framework"].status
            ),
        )


def validate_changes_in_documents(request, document):
    if (
            request.validated["framework"].status == "active"
            and request.validated["framework"].enquiryPeriod.endDate < get_now()
            and (document.title != "sign.p7s"
                 or document.documentType is not None)
    ):
        raise_operation_error(
            request,
            "Can't {} document when enquiry period expires".format(
                OPERATIONS.get(request.method)
            ),
        )