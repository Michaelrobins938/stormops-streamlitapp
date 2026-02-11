#!/usr/bin/env python3
"""Bridge to forward Windows localhost:8502 to WSL localhost:8501"""

import socket
import threading


def forward(source, destination):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            destination.sendall(data)
    except:
        pass
    finally:
        source.close()
        destination.close()


def main():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("0.0.0.0", 8502))
    listener.listen(5)
    print("Bridge active: http://localhost:8502 -> WSL:8501")

    while True:
        client, _ = listener.accept()
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.connect(("127.0.0.1", 8501))
            threading.Thread(target=forward, args=(client, server), daemon=True).start()
            threading.Thread(target=forward, args=(server, client), daemon=True).start()
        except Exception as e:
            print(f"Connection error: {e}")
            client.close()


if __name__ == "__main__":
    main()
