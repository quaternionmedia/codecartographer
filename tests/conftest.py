"""Settings a developer's shell may carry that no test here means to read.

`CODECARTO_CORPUS` points the window at a corpus other than the pin. A test that
places a corpus of its own -- every capability and show test does -- would read
the developer's instead and pass or fail for a reason it never names.
"""

import pytest


@pytest.fixture(autouse=True)
def _no_corpus_override(monkeypatch):
    monkeypatch.delenv("CODECARTO_CORPUS", raising=False)
