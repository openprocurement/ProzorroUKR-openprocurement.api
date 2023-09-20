# -*- coding: utf-8 -*-
import unittest
from copy import deepcopy
from decimal import Decimal

from esculator import npv, escp
from openprocurement.api.tests.base import snitch
from openprocurement.api.utils import get_now

from openprocurement.tender.belowthreshold.tests.base import (
    test_tender_below_organization,
    test_tender_below_author,
)
from openprocurement.tender.belowthreshold.tests.contract import (
    TenderContractResourceTestMixin,
    TenderContractDocumentResourceTestMixin,
)
from openprocurement.tender.belowthreshold.tests.contract_blanks import (
    patch_tender_contract_status_by_owner,
    patch_tender_contract_status_by_others,
    patch_tender_contract_status_by_supplier,
    create_tender_contract_document_by_supplier,
    create_tender_contract_document_by_others,
    put_tender_contract_document_by_supplier,
    put_tender_contract_document_by_others,
    patch_tender_contract_document_by_supplier,
)

from openprocurement.tender.openua.tests.contract_blanks import (
    create_tender_contract,
    patch_tender_contract_datesigned,
)

from openprocurement.tender.openeu.tests.base import test_tender_openeu_data
from openprocurement.tender.esco.tests.base import (
    BaseESCOContentWebTest,
    test_tender_esco_bids,
    NBU_DISCOUNT_RATE,
)

from openprocurement.tender.openeu.tests.contract_blanks import (
    # TenderContractResourceTest
    contract_termination,
)

from openprocurement.tender.esco.tests.contract_blanks import (
    # TenderContractResourceTest
    patch_tender_contract,
)
from openprocurement.tender.esco.procedure.utils import to_decimal

amount_precision = 2

contract_amount_performance = to_decimal(
    npv(
        test_tender_esco_bids[0]["value"]["contractDuration"]["years"],
        test_tender_esco_bids[0]["value"]["contractDuration"]["days"],
        test_tender_esco_bids[0]["value"]["yearlyPaymentsPercentage"],
        test_tender_esco_bids[0]["value"]["annualCostsReduction"],
        get_now(),
        NBU_DISCOUNT_RATE,
    )
).quantize(Decimal(f"1E-{amount_precision}"))

contract_amount = to_decimal(
    escp(
        test_tender_esco_bids[0]["value"]["contractDuration"]["years"],
        test_tender_esco_bids[0]["value"]["contractDuration"]["days"],
        test_tender_esco_bids[0]["value"]["yearlyPaymentsPercentage"],
        test_tender_esco_bids[0]["value"]["annualCostsReduction"],
        get_now(),
    )
).quantize(Decimal(f"1E-{amount_precision}"))


class TenderContractResourceTest(BaseESCOContentWebTest, TenderContractResourceTestMixin):
    initial_status = "active.qualification"
    initial_bids = test_tender_esco_bids
    author_data = test_tender_below_author
    initial_auth = ("Basic", ("broker", ""))
    expected_contract_amountPerformance = contract_amount_performance
    expected_contract_amount = contract_amount

    def setUp(self):
        super(TenderContractResourceTest, self).setUp()
        # Create award
        self.supplier_info = deepcopy(test_tender_below_organization)
        self.app.authorization = ("Basic", ("token", ""))
        response = self.app.post_json(
            "/tenders/{}/awards".format(self.tender_id),
            {
                "data": {
                    "suppliers": [self.supplier_info],
                    "status": "pending",
                    "bid_id": self.initial_bids[0]["id"],
                    "value": self.initial_bids[0]["value"],
                    "items": test_tender_openeu_data["items"],
                }
            },
        )
        award = response.json["data"]
        self.award_id = award["id"]
        self.app.authorization = ("Basic", ("broker", ""))
        response = self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active", "qualified": True, "eligible": True}},
        )

    test_contract_termination = snitch(contract_termination)
    test_create_tender_contract = snitch(create_tender_contract)
    test_patch_tender_contract_datesigned = snitch(patch_tender_contract_datesigned)
    test_patch_tender_contract = snitch(patch_tender_contract)
    test_patch_tender_contract_status_by_owner = snitch(patch_tender_contract_status_by_owner)
    test_patch_tender_contract_status_by_others = snitch(patch_tender_contract_status_by_others)
    test_patch_tender_contract_status_by_supplier = snitch(patch_tender_contract_status_by_supplier)


class TenderContractDocumentResourceTest(BaseESCOContentWebTest, TenderContractDocumentResourceTestMixin):
    initial_status = "active.qualification"
    initial_bids = test_tender_esco_bids
    initial_auth = ("Basic", ("broker", ""))
    docservice = True

    def setUp(self):
        super(TenderContractDocumentResourceTest, self).setUp()
        # Create award
        supplier_info = deepcopy(test_tender_below_organization)
        self.app.authorization = ("Basic", ("token", ""))
        response = self.app.post_json(
            "/tenders/{}/awards".format(self.tender_id),
            {"data": {"suppliers": [supplier_info], "status": "pending", "bid_id": self.initial_bids[0]["id"]}},
        )
        award = response.json["data"]
        self.award_id = award["id"]
        response = self.app.patch_json(
            "/tenders/{}/awards/{}".format(self.tender_id, self.award_id),
            {"data": {"status": "active", "qualified": True, "eligible": True}},
        )
        # Create contract for award
        response = self.app.post_json(
            "/tenders/{}/contracts".format(self.tender_id),
            {"data": {"title": "contract title", "description": "contract description", "awardID": self.award_id}},
        )
        contract = response.json["data"]
        self.contract_id = contract["id"]
        self.app.authorization = ("Basic", ("broker", ""))

    test_create_tender_contract_document_by_supplier = snitch(create_tender_contract_document_by_supplier)
    test_create_tender_contract_document_by_others = snitch(create_tender_contract_document_by_others)
    test_put_tender_contract_document_by_supplier = snitch(put_tender_contract_document_by_supplier)
    test_put_tender_contract_document_by_others = snitch(put_tender_contract_document_by_others)
    test_patch_tender_contract_document_by_supplier = snitch(patch_tender_contract_document_by_supplier)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderContractResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractDocumentResourceTest))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
