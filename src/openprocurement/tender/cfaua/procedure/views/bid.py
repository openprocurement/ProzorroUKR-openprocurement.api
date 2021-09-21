from openprocurement.api.utils import json_view
from openprocurement.tender.openua.procedure.views.bid import TenderBidResource
from openprocurement.tender.core.procedure.models.bid import filter_administrator_bid_update
from openprocurement.tender.cfaua.procedure.models.bid import PostBid, PatchBid, Bid
from openprocurement.tender.cfaua.procedure.state import BidState
from openprocurement.tender.cfaua.procedure.validation import (
    validate_bid_posted_status,
)
from openprocurement.tender.cfaua.procedure.serializers import BidSerializer
from openprocurement.tender.core.procedure.validation import (
    unless_item_owner,
    unless_administrator,
    validate_bid_accreditation_level,
    validate_item_owner,
    validate_input_data,
    validate_patch_data,
    validate_data_documents,
    validate_update_deleted_bid,
    validate_bid_operation_period,
    validate_bid_operation_not_in_tendering,
    validate_bid_operation_in_tendering,
)
from cornice.resource import resource
from logging import getLogger

LOGGER = getLogger(__name__)


@resource(
    name="closeFrameworkAgreementUA:Tender Bids",
    collection_path="/tenders/{tender_id}/bids",
    path="/tenders/{tender_id}/bids/{bid_id}",
    procurementMethodType="closeFrameworkAgreementUA",
    description="Tender EU bids",
)
class TenderBidResource(TenderBidResource):

    state_class = BidState
    serializer_class = BidSerializer

    @json_view(
        permission="view_tender",
        validators=(
            validate_bid_operation_in_tendering,
        )
    )
    def collection_get(self):
        return super().collection_get()

    @json_view(
        permission="view_tender",
        validators=(
            unless_item_owner(
                validate_bid_operation_in_tendering,
                item_name="bid"
            ),
        )
    )
    def get(self):
        return super().get()

    @json_view(
        content_type="application/json",
        permission="create_bid",
        validators=(
            validate_bid_accreditation_level,
            validate_bid_operation_not_in_tendering,
            validate_bid_operation_period,
            validate_input_data(PostBid),
            validate_bid_posted_status,
            validate_data_documents,
        ),
    )
    def collection_post(self):
        return super().collection_post()

    @json_view(
        content_type="application/json",
        permission="edit_bid",
        validators=(
            unless_administrator(validate_item_owner("bid")),
            validate_update_deleted_bid,

            validate_input_data(PatchBid, filters=(filter_administrator_bid_update,), none_means_remove=True),
            validate_patch_data(Bid, item_name="bid"),

            validate_bid_operation_not_in_tendering,
            validate_bid_operation_period,
        ),
    )
    def patch(self):
        return super().patch()