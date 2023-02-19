# -*- coding: utf-8 -*-
import unittest
from copy import deepcopy

from openprocurement.api.tests.base import snitch
from openprocurement.framework.open.tests.base import (
    test_framework_open_data,
    test_open_documents,
    OpenContentWebTest,
    BaseDSOpenContentWebTest,
)
from openprocurement.framework.open.tests.document_blanks import (
    get_documents_list,
    get_document_by_id,
    create_framework_document_forbidden,
    create_framework_document,
    not_found,
    put_contract_document,
    create_framework_document_json_bulk,
)


class TestDocumentGet(OpenContentWebTest):
    initial_data = deepcopy(test_framework_open_data)

    def setUp(self):
        self.initial_data["documents"] = deepcopy(test_open_documents)
        for document in self.initial_data["documents"]:
            document["url"] = self.generate_docservice_url()
        super(TestDocumentGet, self).setUp()

    test_get_documents_list = snitch(get_documents_list)
    test_get_document_by_id = snitch(get_document_by_id)


class TestDocumentsCreate(BaseDSOpenContentWebTest):
    initial_data = test_framework_open_data
    initial_auth = ("Basic", ("broker", ""))

    test_create_framework_document_forbidden = snitch(create_framework_document_forbidden)
    test_create_framework_document = snitch(create_framework_document)
    test_create_framework_document_json_bulk = snitch(create_framework_document_json_bulk)


class OpenDocumentWithDSResourceTest(BaseDSOpenContentWebTest):
    initial_data = test_framework_open_data

    test_not_found = snitch(not_found)
    test_put_contract_document = snitch(put_contract_document)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDocumentGet))
    suite.addTest(unittest.makeSuite(TestDocumentsCreate))
    suite.addTest(unittest.makeSuite(OpenDocumentWithDSResourceTest))
    return suite
