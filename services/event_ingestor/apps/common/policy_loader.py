import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings


@lru_cache(maxsize=1)
def load_permission_policy() -> dict:
    """
    Loads roles: permissions mapping from a JSON file.
    """
    base_dir = Path(settings.BASE_DIR)
    policy_path = base_dir / "apps" / "common" / "policies" / "permissions.json"

    with policy_path.open("r", encoding="utf-8") as f:
        return json.load(f)
