from cornice.resource import resource

from openprocurement.tender.core.procedure.views.cancellation_complaint_post import (
    BaseCancellationComplaintPostResource,
)


@resource(
    name="aboveThresholdUA.defense:Tender Cancellation Complaint Posts",
    collection_path="/tenders/{tender_id}/cancellations/{cancellation_id}/complaints/{complaint_id}/posts",
    path="/tenders/{tender_id}/cancellations/{cancellation_id}/complaints/{complaint_id}/posts/{post_id}",
    procurementMethodType="aboveThresholdUA.defense",
    description="Tender cancellation complaint posts",
)
class OpenUADefenseCancellationComplaintPostResource(BaseCancellationComplaintPostResource):
    pass
