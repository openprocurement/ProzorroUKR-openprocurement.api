from logging import getLogger
from pkg_resources import iter_entry_points

from openprocurement.api.database import COLLECTION_CLASSES
from openprocurement.contracting.core.database import ContractCollection
from openprocurement.contracting.core.utils import ContractTypePredicate


LOGGER = getLogger("openprocurement.contracting.core")


def includeme(config):
    from openprocurement.contracting.core.utils import extract_contract_doc

    LOGGER.info("Init contracting.core plugin.")
    COLLECTION_CLASSES["contracts"] = ContractCollection
    config.add_request_method(extract_contract_doc, "contract_doc", reify=True)
    config.add_route_predicate("contractType", ContractTypePredicate)
    config.scan("openprocurement.contracting.core.procedure.views")

    settings = config.get_settings()
    plugins = settings.get("plugins") and [plugin.strip() for plugin in settings["plugins"].split(",")]
    for entry_point in iter_entry_points("openprocurement.contracting.core.plugins"):
        if not plugins or entry_point.name in plugins:
            plugin = entry_point.load()
            plugin(config)
