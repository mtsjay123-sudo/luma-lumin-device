"""The cloud brain is parked: Luma thinks at home, and nothing in the cloud answers a turn (luma.llm.brain.cloud_allowed,
checked by tests/test_home_brain_only.py). The tests of the cloud brain's machinery turn the switch on for themselves, so
everything it needs stays checked for the day it's brought back. A test module does:

    from cloud_brain_on import setUpModule, tearDownModule  # noqa: F401
"""
import os

_was = None


def setUpModule():
    global _was
    _was = os.environ.get("LUMA_CLOUD_BRAIN")
    os.environ["LUMA_CLOUD_BRAIN"] = "1"


def tearDownModule():
    if _was is None:
        os.environ.pop("LUMA_CLOUD_BRAIN", None)
    else:
        os.environ["LUMA_CLOUD_BRAIN"] = _was
