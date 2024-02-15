from openprocurement.tender.core.procedure.state.award_complaint_document import (
    AwardComplaintDocumentState,
)
from openprocurement.tender.open.constants import STATUS4ROLE


class OpenAwardComplaintDocumentState(AwardComplaintDocumentState):
    allowed_complaint_status_for_role = STATUS4ROLE
    allowed_tender_statuses = (
        "active.enquiries",
        "active.tendering",
        "active.auction",
        "active.qualification",
        "active.awarded",
    )
