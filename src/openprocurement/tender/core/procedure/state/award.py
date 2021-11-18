from openprocurement.tender.core.procedure.context import get_now, get_request, get_tender
from openprocurement.tender.core.utils import calculate_tender_business_date
from openprocurement.tender.core.procedure.contracting import add_contracts
from openprocurement.tender.core.procedure.models.contract import Contract
from openprocurement.tender.core.procedure.state.tender import TenderState
from openprocurement.api.utils import raise_operation_error
from datetime import timedelta


class AwardStateMixing:
    # methods from TenderState class
    add_next_award: callable
    get_change_tender_status_handler: callable

    # procedure configurable value
    award_stand_still_time: timedelta

    def award_on_patch(self, before, award):
        # start complaintPeriod
        if before["status"] != award["status"]:
            if award["status"] in ("active", "unsuccessful"):
                if not award.get("complaintPeriod"):
                    award["complaintPeriod"] = {}
                award["complaintPeriod"]["startDate"] = get_now().isoformat()

            self.award_status_up(before["status"], award["status"], award)

        elif award["status"] == "pending":
            pass  # allowing to update award in pending status
        else:
            raise_operation_error(get_request(),
                                  f"Can't update award in current ({before['status']}) status")

    def award_status_up(self, before, after, award):
        assert before != after, "Statuses must be different"
        tender = get_tender()
        now = get_now().isoformat()

        print(f"swap status {before} -> {after}")
        if before == "pending" and after == "active":
            award["complaintPeriod"]["endDate"] = calculate_tender_business_date(
                get_now(), self.award_stand_still_time, tender, True
            ).isoformat()
            add_contracts(get_request(), award, Contract)
            self.add_next_award()

        elif before == "active" and after == "cancelled":
            if award["complaintPeriod"]["endDate"] > now:
                award["complaintPeriod"]["endDate"] = now

            self.set_award_complaints_cancelled(award)
            self.set_award_contracts_cancelled(award)
            self.add_next_award()

        elif before == "pending" and after == "unsuccessful":
            award["complaintPeriod"]["endDate"] = calculate_tender_business_date(
                get_now(), self.award_stand_still_time, tender, True
            ).isoformat()
            self.add_next_award()

        elif (
            before == "unsuccessful" and after == "cancelled"
            and any(i["status"] in ("claim", "answered", "pending", "resolved")
                    for i in award.get("complaints", ""))
        ):
            if tender["status"] == "active.awarded":
                self.get_change_tender_status_handler("active.qualification")(tender)
                del tender["awardPeriod"]

            award["complaintPeriod"]["endDate"] = now

            skip = True
            for i in tender.get("awards"):
                # skip all award before the context one
                if i["id"] == award["id"]:
                    skip = False
                if skip:
                    continue
                # skip different lot awards
                if i.get("lotID") != award.get("lotID"):
                    continue
                # update complaintPeriod.endDate if there is a need
                if i.get("complaintPeriod") and (
                    not i["complaintPeriod"].get("endDate")
                    or i["complaintPeriod"]["endDate"] > now
                ):
                    i["complaintPeriod"]["endDate"] = now
                i["status"] = "cancelled"
                self.set_award_complaints_cancelled(i)
                self.set_award_contracts_cancelled(i)
            self.add_next_award()
        else:  # any other state transitions are forbidden
            raise_operation_error(get_request(),
                                  f"Can't update award in current ({before}) status")
        # date updated when status updated
        award["date"] = get_now().isoformat()

    # helpers
    @staticmethod
    def set_award_contracts_cancelled(award):
        tender = get_tender()
        for contract in tender.get("contracts", tuple()):
            if contract["awardID"] == award["id"]:
                if contract["status"] != "active":
                    contract["status"] = "cancelled"
                else:
                    raise_operation_error(
                        get_request(),
                        "Can't cancel award contract in active status"
                    )

    @staticmethod
    def set_award_complaints_cancelled(award):
        for complaint in award.get("complaints", ""):
            if complaint["status"] not in ("invalid", "resolved", "declined"):
                complaint["status"] = "cancelled"
                complaint["cancellationReason"] = "cancelled"
                complaint["dateCanceled"] = get_now().isoformat()


# example use
class AwardState(AwardStateMixing, TenderState):
    pass
