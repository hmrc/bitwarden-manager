#!/usr/bin/env python
from bitwarden_manager.temp.external_id_updater import (
    CollectionUpdater,
    GroupUpdater,
    MemberUpdater,
)  # pragma: no cover

if __name__ == "__main__":  # pragma: no cover
    CollectionUpdater().run()
    GroupUpdater().run()
    MemberUpdater().run()
