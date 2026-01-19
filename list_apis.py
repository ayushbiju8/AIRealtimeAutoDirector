
import sounddevice as sd

print(f"PortAudio version: {sd.get_portaudio_version()[1]}")

print("\n--- Host APIs ---")
for api in sd.query_hostapis():
    print(f"Index {sd.query_hostapis().index(api)}: {api['name']} (Devices: {api['devices']})")

print("\n--- Audio Devices ---")
devices = sd.query_devices()
for i, dev in enumerate(devices):
    print(f"{i}: {dev['name']}")
    print(f"    API: {sd.query_hostapis(dev['hostapi'])['name']}")
    print(f"    In: {dev['max_input_channels']}, Out: {dev['max_output_channels']}")
    print(f"    Default SR: {dev['default_samplerate']}")
