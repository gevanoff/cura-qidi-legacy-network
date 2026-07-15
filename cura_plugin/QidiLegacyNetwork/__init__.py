"""Cura plugin entry point.

The protocol library is implemented and tested first. Cura integration is intentionally
kept thin and will be activated once the client is verified against a physical i-Fast.
"""


def getMetaData():
    return {}


def register(app):
    from .plugin import QidiLegacyNetworkPlugin

    return {"output_device": QidiLegacyNetworkPlugin(app)}
