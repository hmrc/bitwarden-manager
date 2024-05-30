import bitwarden_manager.groups_and_collections as GroupsAndCollections


def test_update_user_groups_missing_collection_names() -> None:
    teams = ["Team Name One", "Team Name Two"]
    existing_collections = {"Team Name One": {"id": "ZZZZZZZZ", "externalID": ""}}
    expected = ["Team Name Two"]
    assert expected == GroupsAndCollections.missing_collection_names(teams, existing_collections)


def test_non_ump_based_group_ids() -> None:
    teams = ["team-one", "team-two"]
    groups = {
        "team-one": "id-team-four",
        "team-two": "id-team-two",
        "team-three": "id-team-three",
        "team-four": "id-team-four",
    }
    assert ["id-team-three", "id-team-four"] == GroupsAndCollections.non_ump_based_group_ids(groups=groups, teams=teams)
