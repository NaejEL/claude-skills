"""Toy module executed by the end-to-end scenarios."""


def total(values):
    """Return the sum of the values."""
    result = 0
    for value in values:
        result += value
    return result
