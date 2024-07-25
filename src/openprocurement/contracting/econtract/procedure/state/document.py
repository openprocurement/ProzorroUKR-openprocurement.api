from openprocurement.api.constants import CONTRACT_CONFIDENTIAL_DOCS_FROM
from openprocurement.api.procedure.context import get_tender
from openprocurement.api.procedure.models.document import ConfidentialityTypes
from openprocurement.api.utils import raise_operation_error
from openprocurement.contracting.econtract.procedure.state.contract import (
    EContractState,
)
from openprocurement.tender.core.procedure.state.document import BaseDocumentStateMixing
from openprocurement.tender.core.procedure.utils import tender_created_before

CONFIDENTIAL_DOCS_CAUSES = ("criticalInfrastructure", "civilProtection", "RNBO", "lastHope", "UZ", "defencePurchase")


class EContractDocumentState(BaseDocumentStateMixing, EContractState):
    def validate_document_post(self, data):
        tender = self.request.validated["tender"]
        award = self.request.validated["award"]
        self.validate_cancellation_blocks(self.request, tender, lot_id=award.get("lotID"))

    def document_on_post(self, data):
        super().document_on_post(data)
        self.validate_confidentiality(data)

    def validate_confidentiality(self, data):
        if tender_created_before(CONTRACT_CONFIDENTIAL_DOCS_FROM):
            return
        tender = get_tender()
        if (
            data.get("documentOf") in ("contract", "change")
            and data.get("documentType") in ("contractSigned", "contractAnnexe")
            and tender.get("cause") in CONFIDENTIAL_DOCS_CAUSES
        ):
            if data["confidentiality"] != ConfidentialityTypes.BUYER_ONLY:
                raise_operation_error(
                    self.request,
                    f"Document should be confidential",
                    name="confidentiality",
                    status=422,
                )
        elif data["confidentiality"] == ConfidentialityTypes.BUYER_ONLY:
            raise_operation_error(
                self.request,
                f"Document should be public",
                name="confidentiality",
                status=422,
            )

    def validate_document_patch(self, before, after):
        tender = self.request.validated["tender"]
        award = self.request.validated["award"]
        self.validate_cancellation_blocks(self.request, tender, lot_id=award.get("lotID"))

    def document_on_patch(self, before, after):
        super().document_on_patch(before, after)
        self.validate_confidentiality(after)
