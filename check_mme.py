
import sounddevice as sd
import sys

# Set encoding to utf-8 for console
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

print("Searching for MME devices...")
host_apis = sd.query_hostapis()
for i, api in enumerate(host_apis):
    print(f"Host API {i}: {api['name']}")

print("\nScanning 'iQOO' or 'Hands-Free' devices:")
found = False
for i, dev in enumerate(sd.query_devices()):
    name = dev['name']
    if "iQOO" in name or "Hands-Free" in name:
        api_name = host_apis[dev['hostapi']]['name']
        print(f"Device {i}: {name}")
        print(f"  API: {api_name}")
        print(f"  In: {dev['max_input_channels']}")
        print("-" * 20)
        found = True

if not found:
    print("No matches found.")
