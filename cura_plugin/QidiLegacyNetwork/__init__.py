"""Cura 5 plugin entry point for legacy QIDI network printing."""


def getMetaData():
    return {}


def register(app):
    from .extension import QidiLegacyNetworkExtension
    from .plugin import QidiLegacyNetworkPlugin

    output_plugin = QidiLegacyNetworkPlugin(app)
    extension = QidiLegacyNetworkExtension(output_plugin)
    return {
        "output_device": output_plugin,
        "extension": extension,
    }
