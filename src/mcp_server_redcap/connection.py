import os

import redcap
from dotenv import load_dotenv

load_dotenv()

_project: redcap.Project | None = None


def get_project() -> redcap.Project:
    global _project
    if _project is None:
        url = os.environ.get("REDCAP_URL")
        token = os.environ.get("REDCAP_TOKEN")
        if not url or not token:
            raise RuntimeError(
                "REDCAP_URL and REDCAP_TOKEN environment variables must be set"
            )
        verify_ssl = os.environ.get("REDCAP_VERIFY_SSL", "true").lower() != "false"
        _project = redcap.Project(url, token, verify_ssl=verify_ssl)
    return _project
