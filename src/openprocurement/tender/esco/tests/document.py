import unittest

from openprocurement.tender.belowthreshold.tests.document import (
    TenderDocumentWithDSResourceTestMixin,
)
from openprocurement.tender.esco.tests.base import BaseESCOContentWebTest


class TenderDocumentWithDSResourceTest(BaseESCOContentWebTest, TenderDocumentWithDSResourceTestMixin):
    initial_auth = ("Basic", ("broker", ""))
    docservice = True


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TenderDocumentWithDSResourceTest))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
