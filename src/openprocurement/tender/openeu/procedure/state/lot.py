from openprocurement.tender.openeu.procedure.state.tender_details import OpenEUTenderDetailsState
from openprocurement.tender.core.procedure.state.lot import LotInvalidationBidStateMixin


class TenderLotState(LotInvalidationBidStateMixin, OpenEUTenderDetailsState):
    pass
