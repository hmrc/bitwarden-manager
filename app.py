from bitwarden_manager.bitwarden_manager import BitwardenManager
from typing import Any, Dict
import logging


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Any:
    response = BitwardenManager().run(event=event)
    logging.getLogger().info(response)
    return response
