from bitwarden_manager.temp.external_id_updater import CollectionUpdater, GroupUpdater

if __name__ == "__main__":
    CollectionUpdater().run()
    GroupUpdater().run()
