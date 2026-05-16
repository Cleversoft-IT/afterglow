# Spikes — quick experimental scripts kept outside `tests/` so they do not
# run during the default `pytest tests/ -q` sweep. Each spike has its own
# `pytest.mark.skipif` for the external dependency it exercises.
