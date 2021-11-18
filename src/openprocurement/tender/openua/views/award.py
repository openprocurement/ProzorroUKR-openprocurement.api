# -*- coding: utf-8 -*-
from openprocurement.tender.belowthreshold.utils import add_contracts, add_next_award, set_award_contracts_cancelled
from openprocurement.tender.core.validation import (
    validate_patch_award_data,
    validate_update_award_only_for_active_lots,
    validate_update_award_in_not_allowed_status,
    validate_update_award_with_accepted_complaint,
    validate_operation_with_lot_cancellation_in_pending,
    validate_update_status_before_milestone_due_date,
)
from openprocurement.tender.belowthreshold.views.award import TenderAwardResource
from openprocurement.api.utils import json_view, context_unpack, get_now, raise_operation_error
from openprocurement.tender.core.utils import (
    apply_patch,
    optendersresource,
    save_tender,
    calculate_complaint_business_date,
)
from openprocurement.tender.openua.constants import STAND_STILL_TIME


# @optendersresource(
#     name="aboveThresholdUA:Tender Awards",
#     collection_path="/tenders/{tender_id}/awards",
#     path="/tenders/{tender_id}/awards/{award_id}",
#     description="Tender awards",
#     procurementMethodType="aboveThresholdUA",
# )
class TenderUaAwardResource(TenderAwardResource):

    def pre_save(self):
        now = get_now()

        award = self.request.context
        if "status" in self.request.validated["data"]:
            new_status = self.request.validated["data"]["status"]

            if award.status != new_status and new_status in ["active", "unsuccessful"]:
                award.complaintPeriod = {"startDate": now.isoformat()}

    @json_view(
        content_type="application/json",
        permission="edit_tender",
        validators=(
            validate_patch_award_data,
            validate_operation_with_lot_cancellation_in_pending("award"),
            validate_update_award_in_not_allowed_status,
            validate_update_award_only_for_active_lots,
            validate_update_award_with_accepted_complaint,
            validate_update_status_before_milestone_due_date,
        ),
    )
    def patch(self):
        tender = self.request.validated["tender"]
        award = self.request.context
        award_status = award.status
        self.pre_save()
        apply_patch(self.request, save=False, src=self.request.context.serialize())
        configurator = self.request.content_configurator

        now = get_now()

        if award_status == "pending" and award.status == "active":
            award.complaintPeriod.endDate = calculate_complaint_business_date(now, STAND_STILL_TIME, tender)
            add_contracts(self.request, award, now)
            add_next_award(self.request)
        elif (
            award_status == "active"
            and award.status == "cancelled"
            and any([i.status == "satisfied" for i in award.complaints])
        ):
            for i in tender.awards:
                if i.lotID != award.lotID:
                    continue
                if i.complaintPeriod and (not i.complaintPeriod.endDate or i.complaintPeriod.endDate > now):
                    i.complaintPeriod.endDate = now
                i.status = "cancelled"
                set_award_contracts_cancelled(self.request, i)
            add_next_award(self.request)
        elif award_status == "active" and award.status == "cancelled":
            if award.complaintPeriod.endDate > now:
                award.complaintPeriod.endDate = now
            set_award_contracts_cancelled(self.request, award)
            add_next_award(self.request)
        elif award_status == "pending" and award.status == "unsuccessful":
            award.complaintPeriod.endDate = calculate_complaint_business_date(now, STAND_STILL_TIME, tender)
            add_next_award(self.request)
        elif (
            award_status == "unsuccessful"
            and award.status == "cancelled"
            and any([i.status == "satisfied" for i in award.complaints])
        ):
            if tender.status == "active.awarded":
                tender.status = "active.qualification"
                tender.awardPeriod.endDate = None
            if award.complaintPeriod.endDate > now:
                award.complaintPeriod.endDate = now
            for i in tender.awards:
                if i.lotID != award.lotID:
                    continue
                if i.complaintPeriod and (not i.complaintPeriod.endDate or i.complaintPeriod.endDate > now):
                    i.complaintPeriod.endDate = now
                i.status = "cancelled"
                set_award_contracts_cancelled(self.request, i)
            add_next_award(self.request)
        elif self.request.authenticated_role != "Administrator" and not (
            award_status == "pending" and award.status == "pending"
        ):
            raise_operation_error(self.request, "Can't update award in current ({}) status".format(award_status))
        if save_tender(self.request):
            self.LOGGER.info(
                "Updated tender award {}".format(self.request.context.id),
                extra=context_unpack(self.request, {"MESSAGE_ID": "tender_award_patch"}),
            )
            return {"data": award.serialize("view")}
