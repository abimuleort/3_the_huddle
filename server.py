import selectors
import socket
import datetime

HOST = '0.0.0.0'
PORT = 12345
BUFFER = 4096

clients = {}
sel = selectors.DefaultSelector()
log_file = open("chat.log", "a", encoding="utf-8")


def timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")


def loguear(mensaje):
    log_file.write(mensaje + "\n")
    log_file.flush()


def broadcast(mensaje, remitente=None):
    muertos = []
    for sock in clients:
        if sock != remitente:
            try:
                sock.send(mensaje.encode("utf-8"))
            except Exception:
                muertos.append(sock)
    for sock in muertos:
        desconectar(sock, motivo="socket muerto en broadcast")


def desconectar(sock, motivo="desconexión"):
    if sock in clients:
        nombre = clients[sock]["nombre"]
        mensaje = f"[{timestamp()}] *** {nombre} abandonó el chat ({motivo}) ***"

        del clients[sock]
        try:
            sel.unregister(sock)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass

        broadcast(mensaje, remitente=None)
        loguear(mensaje)
        print(f"Conexión cerrada: {nombre} — {motivo}")


def aceptar_cliente(server_sock):
    conn, addr = server_sock.accept()
    conn.setblocking(True)

    try:
        conn.send("Ingresá tu nombre de usuario: ".encode("utf-8"))
        conn.settimeout(30)
        nombre = conn.recv(BUFFER).decode("utf-8").strip()
        if not nombre:
            nombre = f"Anonimo_{addr[1]}"
    except socket.timeout:
        nombre = f"Anonimo_{addr[1]}"
    except (ConnectionResetError, OSError):
        conn.close()
        return

    conn.setblocking(False)

    clients[conn] = {
        "nombre": nombre,
        "addr": addr,
        "muted": False
    }

    sel.register(conn, selectors.EVENT_READ, data="client")

    mensaje_bienvenida = f"[{timestamp()}] *** {nombre} se unió al chat ***\n"
    broadcast(mensaje_bienvenida, remitente=None)
    loguear(mensaje_bienvenida.strip())
    print(mensaje_bienvenida.strip())


def manejar_cliente(sock):
    try:
        data = sock.recv(BUFFER)

        if not data:
            desconectar(sock, motivo="desconexión limpia")
            return

        texto = data.decode("utf-8").strip()
        nombre = clients[sock]["nombre"]

        if texto == "/exit":
            desconectar(sock, motivo="salida voluntaria")

        elif texto.startswith("/mute "):
            objetivo_nombre = texto[6:].lstrip("@").strip()
            objetivo_sock = next(
                (s for s, info in clients.items() if info["nombre"] == objetivo_nombre),
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

            mensaje = f"[{timestamp()}] {nombre}: {texto}\n"
            broadcast(mensaje, remitente=sock)
            loguear(mensaje.strip())

    except (ConnectionResetError, OSError):
        desconectar(sock, motivo="caída inesperada")


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
                    aceptar_cliente(key.fileobj)
                else:
                    manejar_cliente(key.fileobj)
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        sel.close()
        server_sock.close()
        log_file.close()


if __name__ == "__main__":
    main()