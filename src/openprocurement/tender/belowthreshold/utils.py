# -*- coding: utf-8 -*-
from logging import getLogger
from openprocurement.api.constants import (
    TZ,
    NEW_DEFENSE_COMPLAINTS_FROM,
    NEW_DEFENSE_COMPLAINTS_TO,
    MULTI_CONTRACTS_REQUIRED_FROM,
)
from openprocurement.api.utils import get_now, context_unpack
from openprocurement.tender.core.utils import (
    cleanup_bids_for_cancelled_lots,
    remove_draft_bids,
    calculate_tender_date,
    check_skip_award_complaint_period,
    prepare_bids_for_awarding,
    exclude_unsuccessful_awarded_bids,
)
from openprocurement.tender.core.constants import COMPLAINT_STAND_STILL_TIME
from openprocurement.tender.core.utils import (
    get_first_revision_date,
    CancelTenderLot as BaseCancelTenderLot
)

LOGGER = getLogger("openprocurement.tender.belowthreshold")


class CancelTenderLot(BaseCancelTenderLot):

    @staticmethod
    def add_next_award_method(request):
        return add_next_award(request)


def check_bids(request):
    tender = request.validated["tender"]

    if tender.lots:
        [
            setattr(i.auctionPeriod, "startDate", None)
            for i in tender.lots
            if i.numberOfBids < 2 and i.auctionPeriod and i.auctionPeriod.startDate
        ]
        [
            setattr(i, "status", "unsuccessful")
            for i in tender.lots
            if i.numberOfBids == 0 and i.status == "active"
        ]
        cleanup_bids_for_cancelled_lots(tender)
        if not set([i.status for i in tender.lots]).difference(set(["unsuccessful", "cancelled"])):
            tender.status = "unsuccessful"
        elif max([i.numberOfBids for i in tender.lots if i.status == "active"]) < 2:
            add_next_award(request)
    else:
        if tender.numberOfBids < 2 and tender.auctionPeriod and tender.auctionPeriod.startDate:
            tender.auctionPeriod.startDate = None
        if tender.numberOfBids == 0:
            tender.status = "unsuccessful"
        if tender.numberOfBids == 1:
            add_next_award(request)
    check_ignored_claim(tender)


def check_complaint_status(request, complaint, now=None):
    if not now:
        now = get_now()
    if complaint.status == "answered":
        date = calculate_tender_date(complaint.dateAnswered, COMPLAINT_STAND_STILL_TIME, request.tender)
        if date < now:
            complaint.status = complaint.resolutionType
    elif complaint.status == "pending" and complaint.resolutionType and complaint.dateEscalated:
        complaint.status = complaint.resolutionType
    elif complaint.status == "pending":
        complaint.status = "ignored"


def check_ignored_claim(tender):
    complete_lot_ids = [None] if tender.status in ["complete", "cancelled", "unsuccessful"] else []
    complete_lot_ids.extend([i.id for i in tender.lots if i.status in ["complete", "cancelled", "unsuccessful"]])
    for complaint in tender.complaints:
        if complaint.status == "claim" and complaint.relatedLot in complete_lot_ids:
            complaint.status = "ignored"
    for award in tender.awards:
        for complaint in award.complaints:
            if complaint.status == "claim" and complaint.relatedLot in complete_lot_ids:
                complaint.status = "ignored"


def add_contracts(request, award, now=None):
    tender = request.validated["tender"]
    if tender.buyers and all(item.get("relatedBuyer") for item in tender.items):
        is_multi_contracts = len(tender.buyers) > 1
        contract_value = generate_contract_value(tender, award, zero=is_multi_contracts)
        for buyer in tender.buyers:
            add_contract(
                request, award, contract_value, now, buyer.id
            )
    else:
        contract_value = generate_contract_value(tender, award)
        add_contract(
            request, award, contract_value, now
        )


def add_contract(request, award, contract_value, now=None, buyer_id=None):
    tender = request.validated["tender"]
    contract_model = type(tender).contracts.model_class
    contract_item_model = contract_model.items.model_class
    contract_items = []
    for item in tender.items:
        if not buyer_id or buyer_id == item.relatedBuyer:
            if not hasattr(award, "lotID") or item.relatedLot == award.lotID:
                contract_items.append(contract_item_model(dict(item)))
    server_id = request.registry.server_id
    next_contract_number = len(tender.contracts) + 1
    contract_id = "{}-{}{}".format(tender.tenderID, server_id, next_contract_number)
    tender.contracts.append(
        contract_model(
            {
                "buyerID": buyer_id,
                "awardID": award.id,
                "suppliers": award.suppliers,
                "value": contract_value,
                "date": now or get_now(),
                "items": contract_items,
                "contractID": contract_id,
            }
        )
    )


def generate_contract_value(tender, award, zero=False):
    if award.value:
        value = type(tender).contracts.model_class.value.model_class(dict(award.value.items()))
        if zero:
            value.amount, value.amountNet = 0, 0
        else:
            value.amountNet = award.value.amount
        return value
    return None


def check_status(request):
    tender = request.validated["tender"]
    now = get_now()

    for complaint in tender.complaints:
        check_complaint_status(request, complaint, now)
    for award in tender.awards:
        if award.status == "active" and not any([i.awardID == award.id for i in tender.contracts]):
            add_contracts(request, award, now)
            add_next_award(request)
        for complaint in award.complaints:
            check_complaint_status(request, complaint, now)
    if (
        tender.status == "active.enquiries"
        and not tender.tenderPeriod.startDate
        and tender.enquiryPeriod.endDate.astimezone(TZ) <= now
    ):
        LOGGER.info(
            "Switched tender {} to {}".format(tender.id, "active.tendering"),
            extra=context_unpack(request, {"MESSAGE_ID": "switched_tender_active.tendering"}),
        )
        tender.status = "active.tendering"
        return
    elif (
        tender.status == "active.enquiries"
        and tender.tenderPeriod.startDate
        and tender.tenderPeriod.startDate.astimezone(TZ) <= now
    ):
        LOGGER.info(
            "Switched tender {} to {}".format(tender.id, "active.tendering"),
            extra=context_unpack(request, {"MESSAGE_ID": "switched_tender_active.tendering"}),
        )
        tender.status = "active.tendering"
        return
    elif not tender.lots and tender.status == "active.tendering" and tender.tenderPeriod.endDate <= now:
        LOGGER.info(
            "Switched tender {} to {}".format(tender["id"], "active.auction"),
            extra=context_unpack(request, {"MESSAGE_ID": "switched_tender_active.auction"}),
        )
        tender.status = "active.auction"
        remove_draft_bids(request)
        check_bids(request)
        if tender.numberOfBids < 2 and tender.auctionPeriod:
            tender.auctionPeriod.startDate = None
        return
    elif (
            tender.lots
            and tender.status == "active.tendering"
            and tender.tenderPeriod.endDate <= now
    ):
        LOGGER.info(
            "Switched tender {} to {}".format(tender["id"], "active.auction"),
            extra=context_unpack(request, {"MESSAGE_ID": "switched_tender_active.auction"}),
        )
        tender.status = "active.auction"
        remove_draft_bids(request)
        check_bids(request)
        [setattr(i.auctionPeriod, "startDate", None) for i in tender.lots if i.numberOfBids < 2 and i.auctionPeriod]
        return
    elif not tender.lots and tender.status == "active.awarded":
        standStillEnds = [
            a.complaintPeriod.endDate.astimezone(TZ)
            for a in tender.awards
            if a.complaintPeriod and a.complaintPeriod.endDate
        ]
        if not standStillEnds:
            return
        standStillEnd = max(standStillEnds)
        if standStillEnd <= now:
            check_tender_status(request)
    elif tender.lots and tender.status in ["active.qualification", "active.awarded"]:
        if any([i["status"] in tender.block_complaint_status and i.relatedLot is None for i in tender.complaints]):
            return
        for lot in tender.lots:
            if lot["status"] != "active":
                continue
            lot_awards = [i for i in tender.awards if i.lotID == lot.id]
            standStillEnds = [
                a.complaintPeriod.endDate.astimezone(TZ)
                for a in lot_awards
                if a.complaintPeriod and a.complaintPeriod.endDate
            ]
            if not standStillEnds:
                continue
            standStillEnd = max(standStillEnds)
            if standStillEnd <= now:
                check_tender_status(request)
                return


def check_tender_status(request):
    tender = request.validated["tender"]
    now = get_now()

    if tender.lots:
        if any([i.status in tender.block_complaint_status and i.relatedLot is None for i in tender.complaints]):
            return
        for lot in tender.lots:
            if lot.status != "active":
                continue
            lot_awards = [i for i in tender.awards if i.lotID == lot.id]
            if not lot_awards:
                continue
            last_award = lot_awards[-1]
            pending_complaints = any(
                [i["status"] in tender.block_complaint_status and i.relatedLot == lot.id for i in tender.complaints]
            )
            pending_awards_complaints = any(
                [i.status in tender.block_complaint_status for a in lot_awards for i in a.complaints]
            )
            stand_still_end = calculate_stand_still_end(tender, lot_awards, now)
            in_stand_still = now < stand_still_end
            skip_award_complaint_period = check_skip_award_complaint_period(tender)
            if (
                pending_complaints
                or pending_awards_complaints
                or (in_stand_still and not skip_award_complaint_period)
            ):
                continue
            elif last_award.status == "unsuccessful":
                LOGGER.info(
                    "Switched lot {} of tender {} to {}".format(lot.id, tender.id, "unsuccessful"),
                    extra=context_unpack(request, {"MESSAGE_ID": "switched_lot_unsuccessful"}, {"LOT_ID": lot.id}),
                )
                lot.status = "unsuccessful"
                continue
            elif last_award.status == "active":
                if "agreements" in tender:
                    allow_complete_lot = agreements_allow_to_complete(tender.agreements)
                else:
                    contracts = [
                        contract for contract in tender.contracts
                        if contract.awardID == last_award.id
                    ]
                    allow_complete_lot = contracts_allow_to_complete(contracts)
                if allow_complete_lot:
                    LOGGER.info(
                        "Switched lot {} of tender {} to {}".format(lot.id, tender.id, "complete"),
                        extra=context_unpack(request, {"MESSAGE_ID": "switched_lot_complete"}, {"LOT_ID": lot.id}),
                    )
                    lot.status = "complete"

        statuses = set([lot.status for lot in tender.lots])
        if statuses == set(["cancelled"]):
            LOGGER.info(
                "Switched tender {} to {}".format(tender.id, "cancelled"),
                extra=context_unpack(request, {"MESSAGE_ID": "switched_tender_cancelled"}),
            )
            tender.status = "cancelled"
        elif not statuses.difference(set(["unsuccessful", "cancelled"])):
            LOGGER.info(
                "Switched tender {} to {}".format(tender.id, "unsuccessful"),
                extra=context_unpack(request, {"MESSAGE_ID": "switched_tender_unsuccessful"}),
            )
            tender.status = "unsuccessful"
        elif not statuses.difference(set(["complete", "unsuccessful", "cancelled"])):
            LOGGER.info(
                "Switched tender {} to {}".format(tender.id, "complete"),
                extra=context_unpack(request, {"MESSAGE_ID": "switched_tender_complete"}),
            )
            tender.status = "complete"
    else:
        pending_complaints = any([i.status in tender.block_complaint_status for i in tender.complaints])
        pending_awards_complaints = any(
            [i.status in tender.block_complaint_status for a in tender.awards for i in a.complaints]
        )
        stand_still_end = calculate_stand_still_end(tender, tender.awards, now)
        stand_still_time_expired = stand_still_end < now
        last_award_status = tender.awards[-1].status if tender.awards else ""
        if (
            not pending_complaints
            and not pending_awards_complaints
            and stand_still_time_expired
            and last_award_status == "unsuccessful"
        ):
            LOGGER.info(
                "Switched tender {} to {}".format(tender.id, "unsuccessful"),
                extra=context_unpack(request, {"MESSAGE_ID": "switched_tender_unsuccessful"}),
            )
            tender.status = "unsuccessful"

        contracts = tender.get("contracts", [])
        allow_complete_tender = contracts_allow_to_complete(contracts)
        if allow_complete_tender:
            tender.status = "complete"

    if tender.procurementMethodType == "belowThreshold":
        check_ignored_claim(tender)


def calculate_stand_still_end(tender, lot_awards, now):
    first_revision_date = get_first_revision_date(tender)
    new_defence_complaints = NEW_DEFENSE_COMPLAINTS_FROM < first_revision_date < NEW_DEFENSE_COMPLAINTS_TO
    stand_still_ends = [
        a.complaintPeriod.endDate
        for a in lot_awards
        if (
            a.complaintPeriod
            and a.complaintPeriod.endDate
            and (a.status != "cancelled" if new_defence_complaints else True)
        )
    ]
    return max(stand_still_ends) if stand_still_ends else now


def contracts_allow_to_complete(contracts):
    return (
        contracts
        and any([contract.status == "active" for contract in contracts])
        and not any([contract.status == "pending" for contract in contracts])
    )


def agreements_allow_to_complete(agreements):
    return any([a.status == "active" for a in agreements])


def add_next_award(request):
    """Adding next award.

    :param request:
        The pyramid request object.
    """
    tender = request.validated["tender"]
    now = get_now()
    if not tender.awardPeriod:
        tender.awardPeriod = type(tender).awardPeriod({})
    if not tender.awardPeriod.startDate:
        tender.awardPeriod.startDate = now
    if tender.lots:
        statuses = set()
        for lot in tender.lots:
            if lot.status != "active":
                continue
            lot_awards = [i for i in tender.awards if i.lotID == lot.id]
            if lot_awards and lot_awards[-1].status in ["pending", "active"]:
                statuses.add(lot_awards[-1].status)
                continue
            all_bids = prepare_bids_for_awarding(tender, tender.bids, lot_id=lot.id)
            if all_bids:
                bids = exclude_unsuccessful_awarded_bids(tender, all_bids, lot_id=lot.id)
                if bids:
                    tender.append_award(bids[0], all_bids, lot_id=lot.id)
                    request.response.headers["Location"] = request.route_url(
                        "{}:Tender Awards".format(tender.procurementMethodType),
                        tender_id=tender.id,
                        award_id=tender.awards[-1]["id"]
                    )
                    statuses.add("pending")
                else:
                    statuses.add("unsuccessful")
            else:
                lot.status = "unsuccessful"
                statuses.add("unsuccessful")

        if statuses.difference(set(["unsuccessful", "active"])):
            tender.awardPeriod.endDate = None
            tender.status = "active.qualification"
        else:
            tender.awardPeriod.endDate = now
            tender.status = "active.awarded"
    else:
        if not tender.awards or tender.awards[-1].status not in ["pending", "active"]:
            all_bids = prepare_bids_for_awarding(tender, tender.bids, lot_id=None)
            bids = exclude_unsuccessful_awarded_bids(tender, all_bids, lot_id=None)
            if bids:
                tender.append_award(bids[0], all_bids)
                request.response.headers["Location"] = request.route_url(
                    "{}:Tender Awards".format(tender.procurementMethodType),
                    tender_id=tender.id,
                    award_id=tender.awards[-1]["id"]
                )
        if tender.awards[-1].status == "pending":
            tender.awardPeriod.endDate = None
            tender.status = "active.qualification"
        else:
            tender.awardPeriod.endDate = now
            tender.status = "active.awarded"
