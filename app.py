from bitwarden_manager.bitwarden_manager import BitwardenManager
from typing import Any, Dict


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Any:
    return BitwardenManager().run(event=event)
