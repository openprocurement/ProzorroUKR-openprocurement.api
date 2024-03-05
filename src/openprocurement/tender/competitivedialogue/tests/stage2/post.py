from copy import deepcopy
from unittest.mock import patch

from openprocurement.tender.belowthreshold.tests.base import (
    test_tender_below_cancellation,
    test_tender_below_claim,
    test_tender_below_draft_complaint,
)
from openprocurement.tender.competitivedialogue.tests.base import (
    BaseCompetitiveDialogEUStage2ContentWebTest,
    BaseCompetitiveDialogUAStage2ContentWebTest,
    test_tender_cd_author,
    test_tender_cd_lots,
    test_tender_cd_tenderer,
)
from openprocurement.tender.competitivedialogue.tests.stage2.award import (
    test_tender_bids,
)
from openprocurement.tender.core.tests.utils import change_auth
from openprocurement.tender.openua.tests.post import (
    ClaimPostResourceMixin,
    ComplaintPostResourceMixin,
    TenderAwardComplaintPostResourceMixin,
    TenderCancellationComplaintPostResourceMixin,
    TenderComplaintPostResourceMixin,
    TenderQualificationComplaintPostResourceMixin,
    date_after_2020_04_19,
)


class TenderCompetitiveDialogUAComplaintPostResourceTest(
    BaseCompetitiveDialogUAStage2ContentWebTest, ComplaintPostResourceMixin, TenderComplaintPostResourceMixin
):
    docservice = True
    claim_data = deepcopy(test_tender_below_claim)
    claim_data["author"] = test_tender_cd_author
    initial_lots = test_tender_cd_lots

    def setUp(self):
        super().setUp()
        complaint_data = deepcopy(test_tender_below_draft_complaint)
        complaint_data["author"] = test_tender_cd_author
        response = self.app.post_json(
            "/tenders/{}/complaints".format(self.tender_id),
            {"data": complaint_data},
        )
        self.complaint_id = response.json["data"]["id"]
        self.complaint_owner_token = response.json["access"]["token"]
        self.assertEqual(response.status, "201 Created")
        self.assertEqual(response.content_type, "application/json")


class TenderCompetitiveDialogEUComplaintPostResourceTest(
    BaseCompetitiveDialogEUStage2ContentWebTest, ComplaintPostResourceMixin, TenderComplaintPostResourceMixin
):
    docservice = True
    claim_data = deepcopy(test_tender_below_claim)
    claim_data["author"] = test_tender_cd_author
    initial_lots = test_tender_cd_lots

    def setUp(self):
        super().setUp()
        complaint_data = deepcopy(test_tender_below_draft_complaint)
        complaint_data["author"] = test_tender_cd_author
        response = self.app.post_json(
            "/tenders/{}/complaints".format(self.tender_id),
            {"data": complaint_data},
        )
        self.complaint_id = response.json["data"]["id"]
        self.complaint_owner_token = response.json["access"]["token"]
        self.assertEqual(response.status, "201 Created")
        self.assertEqual(response.content_type, "application/json")


class TenderCompetitiveDialogEUStage2AwardComplaintPostResourceTest(
    BaseCompetitiveDialogEUStage2ContentWebTest,
    ComplaintPostResourceMixin,
    ClaimPostResourceMixin,
    TenderAwardComplaintPostResourceMixin,
):
    docservice = True
    initial_status = "active.tendering"  # 'active.qualification' status sets in setUp
    initial_bids = test_tender_bids
    initial_lots = test_tender_cd_lots

    def setUp(self):
        super().setUp()

        # update periods to have possibility to change tender status by chronograph
        self.set_status("active.pre-qualification", extra={"status": "active.tendering"})

        # simulate chronograph tick
        response = self.check_chronograph()
        self.assertEqual(response.json["data"]["status"], "active.pre-qualification")

        response = self.app.get("/tenders/{}/qualifications".format(self.tender_id))
        self.assertEqual(response.content_type, "application/json")
        qualifications = response.json["data"]
        self.qualification_id = qualifications[0]["id"]

        for qualification in qualifications:
            response = self.app.patch_json(
                "/tenders/{}/qualifications/{}?acc_token={}".format(
                    self.tender_id, qualification["id"], self.tender_token
                ),
                {"data": {"status": "active", "qualified": True, "eligible": True}},
            )
            self.assertEqual(response.status, "200 OK")
            self.assertEqual(response.json["data"]["status"], "active")

        self.set_status("active.qualification")

        # Create award
        with change_auth(self.app, ("Basic", ("token", ""))):
            response = self.app.post_json(
                "/tenders/{}/awards".format(self.tender_id),
                {
                    "data": {
                        "suppliers": [test_tender_cd_tenderer],
                        "status": "pending",
                        "bid_id": self.initial_bids[0]["id"],
                        "lotID": self.initial_lots[0]["id"],
                    }
                },
            )

        award = response.json["data"]
        self.award_id = award["id"]

        with change_auth(self.app, ("Basic", ("token", ""))):
            response = self.app.patch_json(
                "/tenders/{}/awards/{}".format(self.tender_id, self.award_id),
                {"data": {"status": "active", "qualified": True, "eligible": True}},
            )

        # Create complaint for award
        complaint_data = deepcopy(test_tender_below_draft_complaint)
        complaint_data["author"] = test_tender_cd_author
        response = self.app.post_json(
            "/tenders/{}/awards/{}/complaints?acc_token={}".format(
                self.tender_id, self.award_id, self.initial_bids_tokens[self.initial_bids[0]["id"]]
            ),
            {"data": complaint_data},
        )
        self.complaint_id = response.json["data"]["id"]
        self.complaint_owner_token = response.json["access"]["token"]
        self.assertEqual(response.status, "201 Created")
        self.assertEqual(response.content_type, "application/json")


class TenderCompetitiveDialogUAStage2AwardComplaintPostResourceTest(
    BaseCompetitiveDialogUAStage2ContentWebTest,
    ComplaintPostResourceMixin,
    ClaimPostResourceMixin,
    TenderAwardComplaintPostResourceMixin,
):
    docservice = True
    initial_status = "active.qualification"
    initial_bids = test_tender_bids
    initial_lots = test_tender_cd_lots

    def setUp(self):
        super().setUp()
        # Create award
        with change_auth(self.app, ("Basic", ("token", ""))):
            response = self.app.post_json(
                "/tenders/{}/awards".format(self.tender_id),
                {
                    "data": {
                        "suppliers": [test_tender_cd_tenderer],
                        "status": "pending",
                        "bid_id": self.initial_bids[0]["id"],
                        "lotID": self.initial_lots[0]["id"],
                    }
                },
            )

        award = response.json["data"]
        self.award_id = award["id"]

        with change_auth(self.app, ("Basic", ("token", ""))):
            response = self.app.patch_json(
                "/tenders/{}/awards/{}".format(self.tender_id, self.award_id),
                {"data": {"status": "active", "qualified": True, "eligible": True}},
            )

        # Create complaint for award
        complaint_data = deepcopy(test_tender_below_draft_complaint)
        complaint_data["author"] = test_tender_cd_author
        response = self.app.post_json(
            "/tenders/{}/awards/{}/complaints?acc_token={}".format(
                self.tender_id, self.award_id, self.initial_bids_tokens[self.initial_bids[0]["id"]]
            ),
            {"data": complaint_data},
        )
        self.complaint_id = response.json["data"]["id"]
        self.complaint_owner_token = response.json["access"]["token"]
        self.assertEqual(response.status, "201 Created")
        self.assertEqual(response.content_type, "application/json")


class TenderCompetitiveDialogEUQualificationComplaintPostResourceTest(
    BaseCompetitiveDialogEUStage2ContentWebTest,
    ComplaintPostResourceMixin,
    ClaimPostResourceMixin,
    TenderQualificationComplaintPostResourceMixin,
):
    docservice = True
    initial_status = "active.tendering"  # 'active.pre-qualification.stand-still' status sets in setUp
    initial_bids = test_tender_bids
    initial_auth = ("Basic", ("broker", ""))
    author_data = test_tender_cd_author
    initial_lots = test_tender_cd_lots

    def setUp(self):
        super().setUp()

        # update periods to have possibility to change tender status by chronograph
        self.set_status("active.pre-qualification", extra={"status": "active.tendering"})

        # simulate chronograph tick
        response = self.check_chronograph()
        self.assertEqual(response.json["data"]["status"], "active.pre-qualification")

        response = self.app.get("/tenders/{}/qualifications".format(self.tender_id))
        self.assertEqual(response.content_type, "application/json")
        qualifications = response.json["data"]
        self.qualification_id = qualifications[0]["id"]

        for qualification in qualifications:
            response = self.app.patch_json(
                "/tenders/{}/qualifications/{}?acc_token={}".format(
                    self.tender_id, qualification["id"], self.tender_token
                ),
                {"data": {"status": "active", "qualified": True, "eligible": True}},
            )
            self.assertEqual(response.status, "200 OK")
            self.assertEqual(response.json["data"]["status"], "active")

        response = self.app.patch_json(
            "/tenders/{}?acc_token={}".format(self.tender_id, self.tender_token),
            {"data": {"status": "active.pre-qualification.stand-still"}},
        )
        self.assertEqual(response.status, "200 OK")

        # Create complaint for qualification
        complaint_data = deepcopy(test_tender_below_draft_complaint)
        complaint_data["author"] = self.author_data
        response = self.app.post_json(
            "/tenders/{}/qualifications/{}/complaints?acc_token={}".format(
                self.tender_id, self.qualification_id, list(self.initial_bids_tokens.values())[0]
            ),
            {"data": complaint_data},
        )
        complaint = response.json["data"]

        self.complaint_id = complaint["id"]
        self.complaint_owner_token = response.json["access"]["token"]

        self.assertEqual(response.status, "201 Created")
        self.assertEqual(response.content_type, "application/json")


@patch("openprocurement.tender.core.procedure.validation.RELEASE_2020_04_19", date_after_2020_04_19)
class TenderCancellationComplaintPostResourceTest(
    BaseCompetitiveDialogEUStage2ContentWebTest,
    ComplaintPostResourceMixin,
    TenderCancellationComplaintPostResourceMixin,
):
    docservice = True
    initial_lots = test_tender_cd_lots

    @patch("openprocurement.tender.core.procedure.validation.RELEASE_2020_04_19", date_after_2020_04_19)
    def setUp(self):
        super().setUp()

        # Create cancellation
        cancellation = dict(**test_tender_below_cancellation)
        cancellation.update({"reasonType": "noDemand"})
        response = self.app.post_json(
            "/tenders/{}/cancellations?acc_token={}".format(self.tender_id, self.tender_token),
            {"data": cancellation},
        )
        cancellation = response.json["data"]
        self.cancellation_id = cancellation["id"]

        # Add document and update cancellation status to pending

        self.app.post_json(
            "/tenders/{}/cancellations/{}/documents?acc_token={}".format(
                self.tender_id, self.cancellation_id, self.tender_token
            ),
            {
                "data": {
                    "title": "укр.doc",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/msword",
                }
            },
        )
        self.app.patch_json(
            "/tenders/{}/cancellations/{}?acc_token={}".format(self.tender_id, self.cancellation_id, self.tender_token),
            {"data": {"status": "pending"}},
        )

        # Create complaint for cancellation

        response = self.app.post_json(
            "/tenders/{}/cancellations/{}/complaints".format(self.tender_id, self.cancellation_id),
            {"data": test_tender_below_draft_complaint},
        )
        self.complaint_id = response.json["data"]["id"]
        self.complaint_owner_token = response.json["access"]["token"]
        self.assertEqual(response.status, "201 Created")
        self.assertEqual(response.content_type, "application/json")
