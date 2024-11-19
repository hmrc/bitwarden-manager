from bitwarden_manager.bitwarden_manager import BitwardenManager
from typing import Any, Dict


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Any:
    if "bitwarden-manager" in event["path"]: # If this is triggered by an API call, we should return the response.
        return BitwardenManager().run(event)
    else:
        BitwardenManager().run(event)
