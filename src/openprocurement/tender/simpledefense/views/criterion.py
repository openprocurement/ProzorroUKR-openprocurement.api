# -*- coding: utf-8 -*-
from openprocurement.tender.core.utils import optendersresource
from openprocurement.tender.core.views.criterion import BaseTenderCriteriaResource


# @optendersresource(
#     name="simple.defense:Tender Criteria",
#     collection_path="/tenders/{tender_id}/criteria",
#     path="/tenders/{tender_id}/criteria/{criterion_id}",
#     procurementMethodType="simple.defense",
#     description="Tender simple.defense criteria",
# )
class TenderSimpleDefCriteriaResource(BaseTenderCriteriaResource):
    pass

