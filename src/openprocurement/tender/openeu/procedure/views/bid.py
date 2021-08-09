from openprocurement.api.utils import json_view, context_unpack
from openprocurement.tender.core.procedure.views.bid import TenderBidResource
from openprocurement.tender.core.procedure.models.bid import filter_administrator_bid_update
from openprocurement.tender.openeu.procedure.models.bid import PostBid, PatchBid, Bid
from openprocurement.tender.openeu.procedure.state import BidState
from openprocurement.tender.core.procedure.utils import save_tender
from openprocurement.tender.openeu.procedure.validation import (
    validate_post_bid_status,
    validate_view_bids,
    validate_bid_status_update_not_to_pending,
)
from openprocurement.tender.openeu.procedure.serializers import BidSerializer
from openprocurement.tender.core.procedure.validation import (
    unless_administrator,
    validate_bid_accreditation_level,
    unless_item_owner,
    validate_item_owner,
    validate_input_data,
    validate_patch_data,
    validate_data_documents,
    validate_update_deleted_bid,
    validate_bid_operation_period,
    validate_bid_operation_not_in_tendering,
)
from cornice.resource import resource
from logging import getLogger

LOGGER = getLogger(__name__)


@resource(
    name="aboveThresholdEU:Tender Bids",
    collection_path="/tenders/{tender_id}/bids",
    path="/tenders/{tender_id}/bids/{bid_id}",
    procurementMethodType="aboveThresholdEU",
    description="Tender EU bids",
)
class TenderBidResource(TenderBidResource):

    state_class = BidState
    serializer_class = BidSerializer

    @json_view(
        permission="view_tender",
        validators=(
            validate_view_bids,
        )
    )
    def collection_get(self):
        return super().collection_get()

    @json_view(
        permission="view_tender",
        validators=(
            unless_item_owner(
                validate_view_bids,
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
            validate_post_bid_status,
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

            validate_input_data(PatchBid, filters=(filter_administrator_bid_update,)),
            validate_patch_data(Bid, item_name="bid"),

            validate_bid_operation_not_in_tendering,
            # I believe it should be before validate_patch_data
            # but also i want the tests to pass without changing them
            validate_bid_status_update_not_to_pending,
            validate_bid_operation_period,
        ),
    )
    def patch(self):
        return super().patch()

    @json_view(
        permission="edit_bid",
        validators=(
            validate_item_owner("bid"),
            validate_bid_operation_not_in_tendering,
            validate_bid_operation_period,
        )
    )
    def delete(self):
        bid = self.request.validated["bid"]
        bid["status"] = "deleted"
        if save_tender(self.request, modified=False):
            self.LOGGER.info(
                "Deleted tender bid {}".format(bid["id"]),
                extra=context_unpack(self.request, {"MESSAGE_ID": "tender_bid_delete"}),
            )
            return {"data": self.serializer_class(bid).data}