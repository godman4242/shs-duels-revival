#!/usr/bin/env python3
"""
Straw Hat Samurai: Duels — local launcher.
Cross-platform: starts the local emulator server, then opens the game in your
system browser. The SWF is patched to expect http://playerio.localhost:8765/,
which resolves to 127.0.0.1 on all modern OSes.
"""
import os, sys, time, subprocess, webbrowser, socket, signal

PORT = 8765
HOST = "playerio.localhost"
URL = f"http://{HOST}:{PORT}/"

def root():
    return os.path.dirname(os.path.abspath(__file__))

def find_server_script():
    return os.path.join(root(), "solo_server.py")

def is_port_open(host, port, timeout=0.2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def wait_for_server(host, port, seconds=15):
    for _ in range(seconds * 10):
        if is_port_open(host, port):
            return True
        time.sleep(0.1)
    return False

def open_browser(url):
    if sys.platform == "darwin":
        subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif sys.platform == "win32":
        os.startfile(url)
    else:
        # Linux: try xdg-open, sensible-browser, then python webbrowser
        for cmd in ("xdg-open", "sensible-browser"):
            if subprocess.run(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                subprocess.Popen([cmd, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
        webbrowser.open(url, new=2)

def main():
    print("=" * 60)
    print("Straw Hat Samurai: Duels — Local Solo Launcher")
    print("=" * 60)

    # If playerio.localhost does not resolve, warn.
    try:
        socket.getaddrinfo(HOST, None)
    except socket.gaierror:
        print(f"\n⚠️  {HOST} does not resolve for this OS. Browsers resolve *.localhost")
        print("   themselves (RFC 6761), so the game may still load — try it first.")
        print("If the game cannot connect, add this line to your hosts file:")
        print("  127.0.0.1  playerio.localhost")
        print("macOS/Linux: sudo nano /etc/hosts")
        print("Windows:     run Notepad as Administrator and edit C:\\Windows\\System32\\drivers\\etc\\hosts")

    server_script = find_server_script()
    if not os.path.isfile(server_script):
        print(f"❌ solo_server.py not found at {server_script}")
        return 1

    print(f"\n▶ Starting local server on {URL} ...")
    proc = subprocess.Popen(
        [sys.executable, server_script, str(PORT)],
        stdout=sys.stdout, stderr=sys.stderr,
        cwd=root(),
    )

    def cleanup():
        print("\n⏹ Stopping server ...")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    def on_signal(signum=None, frame=None):
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    print("▶ Waiting for server to answer ...")
    # Probe the loopback literal, not the hostname: not every OS resolver maps
    # *.localhost (glibc does not; browsers do), and a failed lookup here would
    # abort a launch that the browser could have handled fine.
    if not wait_for_server("127.0.0.1", PORT):
        print("❌ Server did not start. Check the output above for errors.")
        cleanup()
        return 1

    print(f"▶ Opening browser to {URL} ...")
    open_browser(URL)

    print("\n✅ Game is running. Close this window to stop the server.\n")
    try:
        proc.wait()
    except KeyboardInterrupt:
        cleanup()
    return 0

if __name__ == "__main__":
    sys.exit(main())
