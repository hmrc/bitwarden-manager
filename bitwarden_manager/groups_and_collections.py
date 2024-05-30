from typing import Dict, List


def missing_collection_names(teams: List[str], existing_collections: Dict[str, Dict[str, str]]) -> List[str]:
    return [team for team in teams if not existing_collections.get(team)]


def non_ump_based_group_ids(groups: Dict[str, str], teams: List[str]) -> List[str]:
    return [id for name, id in groups.items() if name not in teams]
