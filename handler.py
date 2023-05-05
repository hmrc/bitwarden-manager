from src.bitwarden_manager import BitwardenManager


def handler(event, context):
    print("handler")
    BitwardenManager().run()
