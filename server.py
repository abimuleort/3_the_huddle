import selectors
import socket
import datetime

HOST = "0.0.0.0"
PORT = 12345
BUFFER = 4096

clients = {}
sel = selectors.DefaultSelector()
log_file = open("chat.log", "a", encoding="utf-8")


def timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")


def login(message):
    log_file.write(message + "\n")
    log_file.flush()


def broadcast(message, sender=None):
    muertos = []
    for sock in clients:
        if sock != sender:
            try:
                sock.send(message.encode("utf-8"))
            except Exception:
                muertos.append(sock)
    for sock in muertos:
        disconnect(sock, motive="socket muerto en broadcast")


def disconnect(sock, motive="desconexión"):
    if sock in clients:
        name = clients[sock]["nombre"]
        message = f"[{timestamp()}] *** {name} abandonó el chat ({motive}) ***"

        del clients[sock]
        try:
            sel.unregister(sock)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass

        broadcast(message, sender=None)
        login(message)
        print(f"Conexión cerrada: {name} — {motive}")


def accept_client(server_sock):
    conn, addr = server_sock.accept()
    conn.setblocking(True)

    try:
        conn.send("Ingresá tu nombre de usuario: ".encode("utf-8"))
        conn.settimeout(30)
        name = conn.recv(BUFFER).decode("utf-8").strip()
        if not name:
            name = f"Anonimo_{addr[1]}"
    except socket.timeout:
        name = f"Anonimo_{addr[1]}"
    except (ConnectionResetError, OSError):
        conn.close()
        return

    conn.setblocking(False)

    clients[conn] = {
        "name": name,
        "addr": addr,
        "muted": False
    }

    sel.register(conn, selectors.EVENT_READ, data="client")

    mensaje_bienvenida = f"[{timestamp()}] *** {name} se unió al chat ***\n"
    broadcast(mensaje_bienvenida, sender=None)
    login(mensaje_bienvenida.strip())
    print(mensaje_bienvenida.strip())


def manage_client(sock):
    try:
        data = sock.recv(BUFFER)

        if not data:
            disconnect(sock, motive="desconexión limpia")
            return

        text = data.decode("utf-8").strip()
        name = clients[sock]["name"]

        if text == "/exit":
            disconnect(sock, motive="salida voluntaria")

        elif text.startswith("/mute "):
            objetivo_nombre = text[6:].lstrip("@").strip()
            objetivo_sock = next(
                (s for s, info in clients.items() if info["name"] == objetivo_nombre),
                None
            )
            if objetivo_sock:
                clients[objetivo_sock]["muted"] = True
                sock.send(f"Muteaste a {objetivo_nombre}\n".encode())
            else:
                sock.send(f"Usuario '{objetivo_nombre}' no encontrado.\n".encode())

        else:
            if clients[sock]["muted"]:
                sock.send("[Estás muteado, nadie te escucha]\n".encode())
                return

            message = f"[{timestamp()}] {name}: {text}\n"
            broadcast(message, sender=sock)
            login(message.strip())

    except (ConnectionResetError, OSError):
        disconnect(sock, motivo="caída inesperada")


def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen()
    server_sock.setblocking(False)

    sel.register(server_sock, selectors.EVENT_READ, data="server")
    print(f"Servidor escuchando en {PORT}...")

    try:
        while True:
            eventos = sel.select(timeout=1)
            for key, mask in eventos:
                if key.data == "server":
                    accept_client(key.fileobj)
                else:
                    manage_client(key.fileobj)
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        sel.close()
        server_sock.close()
        log_file.close()


if __name__ == "__main__":
    main()