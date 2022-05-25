from openprocurement.api.utils import json_view
from openprocurement.tender.core.procedure.views.contract import TenderContractResource
from openprocurement.tender.core.procedure.validation import (
    unless_admins,
    validate_input_data,
    validate_patch_data,
    validate_contract_supplier,
    validate_contract_operation_not_in_allowed_status,
    validate_update_contract_value_with_award,
    validate_update_contract_value_amount,
    validate_update_contract_value_net_required,
    validate_update_contract_status_by_supplier,
    validate_update_contract_status,
    validate_update_contract_value,
    validate_contract_input_data,
)
from openprocurement.tender.pricequotation.procedure.state.contract import PQContractState
from openprocurement.tender.pricequotation.procedure.models.contract import (
    Contract,
    PostContract,
    PatchContract,
    PatchContractSupplier,
)
from cornice.resource import resource
from logging import getLogger

LOGGER = getLogger(__name__)


@resource(
    name="priceQuotation:Tender Contracts",
    collection_path="/tenders/{tender_id}/contracts",
    procurementMethodType="priceQuotation",
    path="/tenders/{tender_id}/contracts/{contract_id}",
    description="Tender contracts",
)
class PQContractResource(TenderContractResource):
    state_class = PQContractState

    @json_view(
        content_type="application/json",
        permission="create_contract",
        validators=(
            validate_input_data(PostContract),
            validate_contract_operation_not_in_allowed_status,
        ),
    )
    def collection_post(self):
        return super().collection_post()

    @json_view(
        content_type="application/json",
        permission="edit_contract",
        validators=(
                unless_admins(validate_contract_supplier()),
                validate_contract_operation_not_in_allowed_status,
                validate_contract_input_data(model=PatchContract, supplier_model=PatchContractSupplier),
                validate_patch_data(Contract, item_name="contract"),
                validate_update_contract_status_by_supplier,
                validate_update_contract_status,
                validate_update_contract_value,
                validate_update_contract_value_net_required,
                validate_update_contract_value_with_award,
                validate_update_contract_value_amount,
        ),
    )
    def patch(self):
        return super().patch()