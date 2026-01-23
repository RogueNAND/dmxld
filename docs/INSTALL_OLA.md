# Installing OLA (Open Lighting Architecture)

## Ubuntu/Debian

### Quick Install (Ubuntu 20.04+, Debian 11+)

```bash
sudo apt-get update
sudo apt-get install -y ola ola-python
```

This installs:
- `ola` - The OLA daemon (olad) and command-line tools
- `ola-python` - Python bindings for OLA

### Verify Installation

```bash
# Check olad version
olad --version

# Check Python bindings
python3 -c "from ola.ClientWrapper import ClientWrapper; print('OLA Python OK')"
```

### Start the OLA Daemon

```bash
# Run in foreground (for testing)
olad -l 3

# Or run as a service
sudo systemctl start olad
sudo systemctl enable olad  # Auto-start on boot
```

### Access the Web UI

Once olad is running, open: http://localhost:9090

From here you can:
- Configure universes and ports
- Patch DMX devices
- Monitor DMX output in real-time

---

## Configuration

### Universe Setup

Edit `/etc/ola/ola-port.conf` or use the web UI to:
1. Create Universe 1
2. Patch a port (e.g., Dummy port for testing, or USB DMX adapter)

### Testing with Dummy Port

The Dummy port outputs to `/dev/null` but allows testing without hardware:

1. Open http://localhost:9090
2. Click "Add Universe"
3. Universe ID: 1, Name: "Test"
4. Patch the Dummy port as output

---

## Troubleshooting

### "Connection refused" errors

```bash
# Check if olad is running
pgrep olad || olad -l 3
```

### Python import errors

```bash
# Ensure ola-python is installed
apt list --installed | grep ola-python

# Check Python path
python3 -c "import ola; print(ola.__file__)"
```

### Permission denied for USB devices

```bash
# Add user to plugdev and olad groups
sudo usermod -aG plugdev,olad $USER
# Log out and back in for group changes to take effect
```

---

## PyDMXShow Integration

Once OLA is installed and olad is running:

```bash
# Test with PyDMXShow
cd /home/rogue/fcld
PYTHONPATH=src:. python3 -m pydmxshow.cli demo-basic

# Or run the example directly
PYTHONPATH=src:. python3 examples/basic_show.py
```

Monitor output in the OLA web UI at http://localhost:9090 → Universe 1 → DMX Console.
