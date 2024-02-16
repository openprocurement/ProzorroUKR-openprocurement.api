from cornice.resource import resource

from openprocurement.tender.core.procedure.views.complaint_post_document import (
    BaseTenderComplaintPostDocumentResource,
)


@resource(
    name="simple.defense:Tender Complaint Post Documents",
    collection_path="/tenders/{tender_id}/complaints/{complaint_id}/posts/{post_id}/documents",
    path="/tenders/{tender_id}/complaints/{complaint_id}/posts/{post_id}/documents/{document_id}",
    procurementMethodType="simple.defense",
    description="Tender complaint post documents",
)
class SimpleDefenseComplaintPostDocumentResource(BaseTenderComplaintPostDocumentResource):
    pass
