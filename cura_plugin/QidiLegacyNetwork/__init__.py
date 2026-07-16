"""Cura 5 plugin entry point for legacy QIDI network printing."""


def getMetaData():
    return {}


def register(app):
    from .plugin import QidiLegacyNetworkPlugin

    return {"output_device": QidiLegacyNetworkPlugin(app)}
