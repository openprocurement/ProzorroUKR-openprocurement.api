from openprocurement.tender.core.procedure.context import get_now, get_request
from openprocurement.tender.core.procedure.state.tender import TenderState
from openprocurement.tender.core.procedure.models.qualification import Qualification
from openprocurement.tender.cfaua.procedure.models.agreement import Agreement
from openprocurement.tender.cfaua.procedure.awarding import add_next_awards
from openprocurement.tender.core.utils import calculate_tender_business_date
from openprocurement.api.utils import context_unpack
from openprocurement.tender.cfaua.constants import CLARIFICATIONS_UNTIL_PERIOD
from logging import getLogger

LOGGER = getLogger(__name__)


class CFAUATenderTenderState(TenderState):
    min_bids_number = 3
    active_bid_statuses = ("active", "pending")
    block_tender_complaint_status = ("claim", "pending", "accepted", "satisfied", "stopping")
    block_complaint_status = ("pending", "accepted", "satisfied", "stopping")

    @staticmethod
    def add_next_award(request):
        add_next_awards(get_request())

    def contract_events(self, tender):
        yield from ()   # empty , this procedure doesn't have contracts

    def qualification_stand_still_events(self, tender):
        active_lots = [lot["id"] for lot in tender.get("lots", "") if lot["status"] == "active"]
        award_period_end = tender.get("awardPeriod", {}).get("endDate")
        if (
            award_period_end
            and award_period_end <= get_now().isoformat()
            and not any(
                i["status"] in self.block_complaint_status
                for a in tender.get("awards", "")
                for i in a.get("complaints", "")
                if a["lotID"] in active_lots
            )
        ):
            yield award_period_end, self.qualification_stand_still_handler

    # handlers
    def tendering_end_handler(self, tender):
        for complaint in tender.get("complaints", ""):
            if complaint.get("status") == "answered" and complaint.get("resolutionType"):
                complaint["status"] = complaint["resolutionType"]

        handler = self.get_change_tender_status_handler("active.pre-qualification")
        handler(tender)
        tender["qualificationPeriod"] = {"startDate": get_now().isoformat()}

        self.remove_draft_bids(tender)
        self.check_bids_number(tender)
        self.prepare_qualifications(tender)

    def qualification_stand_still_handler(self, tender):
        statuses = set()
        for lot in tender.get("lots", ""):
            active_awards_count = sum(1 for i in tender.get("awards", "")
                                      if i["lotID"] == lot["id"] and i["status"] == "active")
            if active_awards_count < self.min_bids_number:
                LOGGER.info(
                    "Switched lot {} of tender {} to {}".format(lot["id"], tender["_id"], "unsuccessful"),
                    extra=context_unpack(get_request(), {"MESSAGE_ID": "switched_lot_unsuccessful"},
                                         {"LOT_ID": lot["id"]}),
                )
                lot["status"] = "unsuccessful"
            statuses.add(lot["status"])

        if not statuses.difference({"unsuccessful"}):
            self.get_change_tender_status_handler("unsuccessful")(tender)
        else:
            self.get_change_tender_status_handler("active.awarded")(tender)
            clarification_date = calculate_tender_business_date(get_now(), CLARIFICATIONS_UNTIL_PERIOD, tender, False)
            tender["contractPeriod"] = {
                "startDate": get_now().isoformat(),
                "clarificationsUntil": clarification_date.isoformat()
            }
            self.prepare_agreements(tender)

    def cancellation_compl_period_end_handler(self, cancellation):
        def handler(tender):
            complaint_statuses = ("invalid", "declined", "stopped", "mistaken", "draft")
            if all(i["status"] in complaint_statuses for i in cancellation.get("complaints", "")):
                cancellation["status"] = "active"

                from openprocurement.tender.core.validation import (
                    validate_absence_of_pending_accepted_satisfied_complaints,
                )
                # TODO: chronograph expects 422 errors ?
                validate_absence_of_pending_accepted_satisfied_complaints(get_request(), cancellation)

                if cancellation.get("relatedLot"):
                    # 1
                    related_lot = cancellation["relatedLot"]
                    for lot in tender["lots"]:
                        if lot["id"] == related_lot:
                            lot["status"] = "cancelled"
                    cancelled_lots = {i["id"] for i in tender["lots"] if i["status"] == "cancelled"}
                    cancelled_items = {i["id"] for i in tender.get("items", "")
                                       if i.get("relatedLot") in cancelled_lots}
                    cancelled_features = {
                        i["code"]
                        for i in tender.get("features", "")
                        if i["featureOf"] == "lot" and i["relatedItem"] in cancelled_lots
                        or i["featureOf"] == "item" and i["relatedItem"] in cancelled_items
                    }

                    # 2 additionally cancel agreements
                    agreements = tender.get("agreements")
                    if tender["status"] == "active.awarded" and agreements:
                        for agreement in agreements:
                            if agreement["items"][0]["relatedLot"] in cancelled_lots:
                                agreement["status"] = "cancelled"

                    # 3 invalidate bids
                    if tender["status"] in (
                        "active.tendering",
                        "active.pre-qualification",
                        "active.pre-qualification.stand-still",
                        "active.auction",
                    ):
                        def filter_docs(b, key):
                            if b.get(key):
                                b[key] = [i for i in b[key]
                                          if i.get("documentOf") != "lot"
                                          or i["relatedItem"] not in cancelled_lots]

                        for bid in tender.get("bids", ""):
                            if tender["status"] == "active.tendering":
                                filter_docs(bid, "documents")
                            filter_docs(bid, "financialDocuments")
                            filter_docs(bid, "eligibilityDocuments")
                            filter_docs(bid, "qualificationDocuments")
                            bid["parameters"] = [i for i in bid.get("parameters", "")
                                                 if i["code"] not in cancelled_features]
                            bid["lotValues"] = [i for i in bid.get("lotValues", "")
                                                if i["relatedLot"] not in cancelled_lots]
                            if not bid["lotValues"] and bid["status"] in ["pending", "active"]:
                                if tender["status"] == "active.tendering":
                                    bid["status"] = "invalid"
                                else:
                                    bid["status"] = "invalid.pre-qualification"
                    # 4 tender status
                    lot_statuses = {lot["status"] for lot in tender["lots"]}
                    if lot_statuses == {"cancelled"}:
                        if tender["status"] in ("active.tendering", "active.auction"):
                            tender["bids"] = []
                        self.get_change_tender_status_handler("cancelled")(tender)

                    elif not lot_statuses.difference({"unsuccessful", "cancelled"}):
                        self.get_change_tender_status_handler("unsuccessful")(tender)
                    elif not lot_statuses.difference({"complete", "unsuccessful", "cancelled"}):
                        self.get_change_tender_status_handler("complete")(tender)

                    # 5 no need to make add_next_award for active lots, because there is only one and it's cancelled
                else:
                    if tender["status"] == "active.tendering":
                        tender["bids"] = []

                    elif tender["status"] in (
                        "active.pre-qualification",
                        "active.pre-qualification.stand-still",
                        "active.auction",
                    ):
                        for bid in tender.get("bids", ""):
                            if bid["status"] in ("pending", "active"):
                                bid["status"] = "invalid.pre-qualification"

                    self.get_change_tender_status_handler("cancelled")(tender)

                    for agreement in tender.get("agreements", ""):
                        if agreement["status"] in ("pending", "active"):
                            agreement["status"] = "cancelled"
        return handler

    # utils
    @staticmethod
    def prepare_agreements(tender):
        if "agreements" not in tender:
            tender["agreements"] = []

        for lot in tender.get("lots"):
            if lot["status"] == "active":
                items = [i for i in tender.get("items", "") if i.get("relatedLot") == lot["id"]]
                unit_prices = [
                    {
                        "relatedItem": item["id"],
                        "value": {
                            "currency": tender["value"]["currency"],
                            "valueAddedTaxIncluded": tender["value"]["valueAddedTaxIncluded"]
                        },
                    } for item in items
                ]

                contracts = []
                for award in tender.get("awards", ""):
                    if award["lotID"] == lot["id"] and award["status"] == "active":
                        contracts.append(
                            {
                                "suppliers": award["suppliers"],
                                "awardID": award["id"],
                                "bidID": award["bid_id"],
                                "date": get_now().isoformat(),
                                "unitPrices": unit_prices,
                                "parameters": [
                                    b for b in tender.get("bids", "")
                                    if b["id"] == award["bid_id"]
                                ][0].get("parameters", []),
                            }
                        )
                server_id = get_request().registry.server_id
                data = {
                    "agreementID": f"{tender['tenderID']}-{server_id}{len(tender.get('agreements', '')) + 1}",
                    "date": get_now().isoformat(),
                    "contracts": contracts,
                    "items": items,
                    "features": tender.get("features", []),
                }
                agreement = Agreement(data)
                tender["agreements"].append(
                    agreement.serialize()
                )

    @staticmethod
    def prepare_qualifications(tender):
        if "qualifications" not in tender:
            tender["qualifications"] = []
        active_lots = tuple(lot["id"] for lot in tender.get("lots", "") if lot["status"] == "active")
        for bid in tender.get("bids", ""):
            if bid["status"] not in ("invalid", "deleted"):
                for lotValue in bid.get("lotValues", ""):
                    if lotValue["status"] == "pending" and lotValue["relatedLot"] in active_lots:
                        qualification = Qualification({
                            "bidID": bid["id"],
                            "status": "pending",
                            "lotID": lotValue["relatedLot"],
                            "date": get_now().isoformat()
                        }).serialize()
                        tender["qualifications"].append(qualification)