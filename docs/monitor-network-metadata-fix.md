# Cura Monitor network metadata correction

Cura's Monitor stage evaluates the active machine stack's network metadata separately from the registered `PrinterOutputDevice`.

The QIDI i-Fast definition and live registration must therefore provide both:

- `supports_network_connection = true`
- configured connection type `2` (LAN/network)

The plugin applies these values to the live stack so existing i-Fast instances created before the definition correction do not need to be deleted and recreated.
