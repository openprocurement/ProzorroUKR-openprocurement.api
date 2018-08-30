# -*- coding: utf-8 -*-
import unittest

from openprocurement.api.tests.base import snitch

from openprocurement.tender.belowthreshold.tests.tender import TenderResourceTestMixin
from openprocurement.tender.belowthreshold.tests.tender_blanks import (
    #TenderProcessTest
    invalid_tender_conditions,
    #TenderResourceTest
    guarantee,
)
from openprocurement.tender.openua.tests.tender_blanks import (
    empty_listing, tender_fields
)
from openprocurement.tender.cfaua.constants import MIN_BIDS_NUMBER
from openprocurement.tender.cfaua.tests.base import (
    test_tender_data,
    BaseTenderWebTest,
    BaseTenderContentWebTest,
    test_lots,
    test_bids,
)
from openprocurement.tender.cfaua.tests.tender_blanks import (
    # TenderProcessTest
    one_bid_tender,
    unsuccessful_after_prequalification_tender,
    one_qualificated_bid_tender,
    multiple_bidders_tender,
    lost_contract_for_active_award,
    # TenderResourceTest
    create_tender_invalid,
    create_tender_generated,
    patch_tender,
    patch_tender_period,
    tender_contract_period,
    invalid_bid_tender_features,
    invalid_bid_tender_lot,
    # TenderTest
    simple_add_tender,
    patch_tender_active_qualification_2_active_qualification_stand_still,
    switch_tender_to_active_awarded,
    patch_max_awards,
    awards_to_bids_number,
    active_qualification_to_act_pre_qualification_st,
    active_pre_qualification_to_act_qualification_st,
    agreement_duration_period,
    tender_features_invalid,
)



class TenderTest(BaseTenderWebTest):

    initial_auth = ('Basic', ('broker', ''))
    initial_data = test_tender_data

    test_simple_add_tender = snitch(simple_add_tender)
    test_agreement_duration_period = snitch(agreement_duration_period)


class TenderCheckStatusTest(BaseTenderContentWebTest):

    test_active_qualification_to_act_pre_qualification_st = snitch(active_qualification_to_act_pre_qualification_st)
    test_active_pre_qualification_to_act_qualification_st = snitch(active_pre_qualification_to_act_qualification_st)


class TenderResourceTest(BaseTenderWebTest, TenderResourceTestMixin):

    initial_auth = ('Basic', ('broker', ''))
    initial_data = test_tender_data
    initial_lots = test_lots
    # test_lots_data = test_lots  # TODO: change attribute identifier
    test_bids_data = test_bids
    min_bids_number = MIN_BIDS_NUMBER

    test_empty_listing = snitch(empty_listing)
    #test_tender_fields = snitch(tender_fields)  added new field need to copy and fix this test
    test_patch_tender_period = snitch(patch_tender_period)
    test_tender_contract_period = snitch(tender_contract_period)
    test_create_tender_invalid = snitch(create_tender_invalid)
    test_create_tender_generated = snitch(create_tender_generated)
    test_patch_tender = snitch(patch_tender)
    test_guarantee = snitch(guarantee)
    test_invalid_bid_tender_features = snitch(invalid_bid_tender_features)
    test_invalid_bid_tender_lot = snitch(invalid_bid_tender_lot)
    test_patch_max_awards = snitch(patch_max_awards)
    test_awards_to_bids_number = snitch(awards_to_bids_number)
    test_tender_features_invalid = snitch(tender_features_invalid)

    def test_patch_not_author(self):
        response = self.app.post_json('/tenders', {'data': test_tender_data})
        self.assertEqual(response.status, '201 Created')
        tender = response.json['data']
        owner_token = response.json['access']['token']

        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('bot', 'bot'))

        response = self.app.post('/tenders/{}/documents'.format(tender['id']),
                                 upload_files=[('file', 'name.doc', 'content')])
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        doc_id = response.json["data"]['id']
        self.assertIn(doc_id, response.headers['Location'])

        self.app.authorization = authorization
        response = self.app.patch_json('/tenders/{}/documents/{}?acc_token={}'.format(tender['id'], doc_id, owner_token),
                                       {"data": {"description": "document description"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Can update document only author")


class TenderProcessTest(BaseTenderWebTest):

    initial_auth = ('Basic', ('broker', ''))
    initial_data = test_tender_data
    initial_lots = test_lots
    test_bids_data = test_bids

    test_invalid_tender_conditions = snitch(invalid_tender_conditions)
    test_one_bid_tender = snitch(one_bid_tender)
    test_unsuccessful_after_prequalification_tender = snitch(unsuccessful_after_prequalification_tender)
    test_one_qualificated_bid_tender = snitch(one_qualificated_bid_tender)

    # test_multiple_bidders_tender = snitch(multiple_bidders_tender)    TODO REWRITE TEST
    # test_lost_contract_for_active_award = snitch(lost_contract_for_active_award)   TODO REWRITE TEST


class TenderPendingAwardsResourceTest(BaseTenderContentWebTest):
    initial_auth = ('Basic', ('broker', ''))
    initial_bids = test_bids

    def setUp(self):
        super(TenderPendingAwardsResourceTest, self).setUp()
        # switch to active.pre-qualification
        self.time_shift('active.pre-qualification')
        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {"data": {"id": self.tender_id}})
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json['data']['status'], "active.pre-qualification")

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/qualifications?acc_token={}'.format(self.tender_id, self.tender_token))
        for qualific in response.json['data']:
            response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(
                self.tender_id, qualific['id'], self.tender_token), {'data': {"status": "active", "qualified": True, "eligible": True}})
            self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
                                       {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")

        self.set_status('active.auction')

        patch_data = {'bids': []}
        for x in range(self.min_bids_number):
            patch_data['bids'].append({
                "id": self.initial_bids[x]['id'],
                "lotValues": [{
                    "value": {
                        "amount": 409 + x * 10,
                        "currency": "UAH",
                        "valueAddedTaxIncluded": True,
                    },
                    "relatedLot": self.initial_lots[0]['id']
                }]
            })

        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.post_json('/tenders/{}/auction/{}'.format(self.tender_id, self.initial_lots[0]['id']),
                                      {'data': patch_data})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        tender = response.json['data']

        for x in range(self.min_bids_number):
            self.assertEqual(tender["bids"][x]['lotValues'][0]['value']['amount'],
                             patch_data["bids"][x]['lotValues'][0]['value']['amount'])
            self.assertEqual(tender["awards"][x]['status'], 'pending')  # all awards are in pending status

    test_patch_tender_active_qualification_2_active_qualification_stand_still = \
        snitch(patch_tender_active_qualification_2_active_qualification_stand_still)
    test_switch_tender_to_active_awarded = snitch(switch_tender_to_active_awarded)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderProcessTest))
    suite.addTest(unittest.makeSuite(TenderResourceTest))
    suite.addTest(unittest.makeSuite(TenderTest))
    suite.addTest(unittest.makeSuite(TenderPendingAwardsResourceTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
