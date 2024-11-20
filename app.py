from bitwarden_manager.bitwarden_manager import BitwardenManager
from typing import Any, Dict

def is_api_gateway_event(event: Dict[str, Any]) -> bool:
    return event.get("path") and "/bitwarden-manager/" in event["path"]

def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any] | None:
    if is_api_gateway_event(event=event):
        return BitwardenManager().api_run(event=event)
    else:
        BitwardenManager().run(event=event)
