import socket
import selectors
import types
from datetime import datetime

HOST = '0.0.0.0'
PORT = 5000

selector = selectors.DefaultSelector()
clients = {}  # socket: username


def broadcast(message, sender_socket=None):
    for client in list(clients.keys()):
        if client != sender_socket:
            try:
                client.sendall(message.encode())
            except:
                remove_client(client)


def remove_client(sock):
    username = clients.get(sock, "Unknown")
    print(f"[INFO] {username} disconnected.")
    selector.unregister(sock)
    sock.close()
    del clients[sock]
    broadcast(f"[SYSTEM] {username} left the chat.\n")


def accept_connection(server_socket):
    conn, addr = server_socket.accept()
    print(f"[NEW CONNECTION] {addr}")
    conn.setblocking(False)
    selector.register(conn, selectors.EVENT_READ, read_message)


def read_message(conn):
    try:
        data = conn.recv(1024).decode().strip()

        if not data:
            remove_client(conn)
            return

        if conn not in clients:

            clients[conn] = data
            broadcast(f"[SYSTEM] {data} joined the chat.\n")
            return

        username = clients[conn]

        if data == "/exit":
            remove_client(conn)
            return

        if data == "/help":
            conn.sendall("Commands: /exit, /help\n".encode())
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[{timestamp}] {username}: {data}\n"

        print(message.strip())
        broadcast(message, conn)

        # Log
        with open("chat_log.txt", "a", encoding="utf-8") as f:
            f.write(message)

    except:
        remove_client(conn)


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)



if __name__ == "__main__":
    main()