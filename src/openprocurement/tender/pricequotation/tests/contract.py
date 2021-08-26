# -*- coding: utf-8 -*-
import unittest
from openprocurement.api.tests.base import snitch
from openprocurement.tender.pricequotation.tests.base import (
    TenderContentWebTest,
    test_bids,
    test_tender_data_multi_buyers,
)
from openprocurement.tender.belowthreshold.tests.contract import (
    TenderContractResourceTestMixin,
    TenderContractDocumentResourceTestMixin,
)
from openprocurement.tender.belowthreshold.tests.contract_blanks import (
    create_tender_contract,
    create_tender_contract_in_complete_status,
    patch_tender_contract_value,
    patch_contract_single_item_unit_value,
    patch_contract_single_item_unit_value_with_status,
    patch_contract_multi_items_unit_value,
    patch_tender_multi_contracts,
    patch_tender_multi_contracts_cancelled,
    patch_tender_multi_contracts_active_cancelled,
)
from openprocurement.tender.pricequotation.tests.contract_blanks import (
    patch_tender_contract,
    patch_tender_contract_value_vat_not_included,
)


class TenderContractResourceTest(TenderContentWebTest,
                                 TenderContractResourceTestMixin):
    initial_status = "active.awarded"
    initial_bids = test_bids

    def get_award(self):
        self.award_id = self.award_ids[-1]
        resp = self.app.get(
            "/tenders/{}/awards/{}".format(self.tender_id, self.award_id),
        )
        award = resp.json["data"]
        self.award_value = award["value"]
        self.award_suppliers = award["suppliers"]
        self.award_items = award["items"]
        self.award_date = award["date"]

    def setUp(self):
        super(TenderContractResourceTest, self).setUp()
        self.get_award()

    test_create_tender_contract = snitch(create_tender_contract)
    test_create_tender_contract_in_complete_status = snitch(
        create_tender_contract_in_complete_status
    )
    test_patch_tender_contract = snitch(patch_tender_contract)
    test_patch_tender_contract_value = snitch(patch_tender_contract_value)
    test_patch_contract_single_item_unit_value = snitch(patch_contract_single_item_unit_value)
    test_patch_contract_single_item_unit_value_with_status = snitch(
        patch_contract_single_item_unit_value_with_status
    )
    test_patch_contract_multi_items_unit_value = snitch(patch_contract_multi_items_unit_value)


class TenderContractVATNotIncludedResourceTest(TenderContentWebTest,
                                               TenderContractResourceTestMixin):
    initial_status = "active.awarded"
    initial_bids = test_bids

    def setUp(self):
        super(TenderContractVATNotIncludedResourceTest, self).setUp()
        TenderContractResourceTest.get_award(self)

    test_patch_tender_contract_value_vat_not_included = snitch(
        patch_tender_contract_value_vat_not_included
    )


class TenderContractDocumentResourceTest(TenderContentWebTest,
                                         TenderContractDocumentResourceTestMixin):
    initial_status = "active.awarded"
    initial_bids = test_bids

    def setUp(self):
        super(TenderContractDocumentResourceTest, self).setUp()


class TenderContractMultiBuyersResourceTest(TenderContentWebTest):
    initial_data = test_tender_data_multi_buyers
    initial_status = "active.qualification"
    initial_bids = test_bids

    def setUp(self):
        super(TenderContractMultiBuyersResourceTest, self).setUp()
        TenderContractResourceTest.get_award(self)
        response = self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active"}},
        )

    test_patch_tender_multi_contracts = snitch(patch_tender_multi_contracts)
    test_patch_tender_multi_contracts_cancelled = snitch(patch_tender_multi_contracts_cancelled)
    test_patch_tender_multi_contracts_active_cancelled = snitch(patch_tender_multi_contracts_active_cancelled)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderContractResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractDocumentResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractMultiBuyersResourceTest))

    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
