# ---------- Importacion de Librerias ----------
import selectors  # Permite manejar multiples conexiones al mismo tiempo
import socket
import datetime   # Permite trabajar con fecha y hora
import json       # Para guardar/cargar estado de clientes
import os         # Para verificar existencia de archivos

# ---------- Definicion de Constantes ----------
HOST = "0.0.0.0"         # Acepta conexiones desde cualquier IP
PORT = 12345              # Puerto del servidor
BUFFER = 4096             # Tamaño del buffer para recibir mensajes
STATE_FILE = "clients_state.json"  # Archivo de estado persistente

clients = {}                                        # Guarda todos los clientes conectados
sel = selectors.DefaultSelector()                   # Crea el selector principal
log_file = open("chat.log", "a", encoding="utf-8")  # Guarda historial

# ---------- Carga de Estado Previo ----------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state():
    state = {}
    for sock, info in clients.items():
        state[info["name"]] = {"name": info["name"], "muted": info["muted"]}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)

# Estado previo cargado al iniciar: { "nombre": {"name": ..., "muted": ...} }
previous_state = load_state()

# ---------- Funcion Tiempo ----------
def timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")

# ---------- Funcion Login ----------
def login(message):
    log_file.write(message + "\n")
    log_file.flush()

# ---------- Funcion Broadcast ----------
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

# ---------- Funcion Desconexion ----------
def disconnect(sock, motive="desconexión"):
    if sock not in clients:
        return
    name = clients.pop(sock)["name"]
    message = f"[{timestamp()}] *** {name} abandonó el chat ({motive}) ***"
    try:
        sel.unregister(sock)
    except Exception:
        pass
    try:
        sock.close()
    except Exception:
        pass
    save_state()
    broadcast(message)
    login(message)
    print(message)

# ---------- Funcion Aceptar Cliente ----------
def accept_client(server_sock):
    conn, addr = server_sock.accept()
    conn.setblocking(True)

    try:
        # Siempre enviamos el prompt, el cliente responde con su nombre guardado
        conn.send("Ingresá tu nombre de usuario: ".encode("utf-8"))
        conn.settimeout(30)
        raw = conn.recv(BUFFER).decode("utf-8").strip()
        name = raw if raw else f"Anonimo_{addr[1]}"
    except socket.timeout:
        name = f"Anonimo_{addr[1]}"
    except (ConnectionResetError, OSError):
        conn.close()
        return

    # Verificar si el nombre corresponde a un cliente previo
    if name in previous_state:
        muted = previous_state[name].get("muted", False)
        is_reconnect = True
    else:
        muted = False
        is_reconnect = False

    conn.setblocking(False)
    clients[conn] = {"name": name, "addr": addr, "muted": muted}
    sel.register(conn, selectors.EVENT_READ, data="client")
    save_state()

    # Confirmar al cliente si es reconexion o ingreso nuevo
    try:
        conn.setblocking(True)
        if is_reconnect:
            conn.send(f"OK_RECONNECT:{name}\n".encode("utf-8"))
        else:
            conn.send(f"OK_NEW:{name}\n".encode("utf-8"))
        conn.setblocking(False)
    except Exception:
        pass

    if is_reconnect:
        message = f"[{timestamp()}] *** {name} reconectó al servidor ***"
    else:
        message = f"[{timestamp()}] *** {name} se unió al chat ***"

    broadcast(message)
    login(message)
    print(message)

# ---------- Funcion Manejo del Cliente ----------
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
                (s for s, info in clients.items() if info["name"] == objetivo_nombre), None
            )
            if objetivo_sock:
                clients[objetivo_sock]["muted"] = True
                save_state()
                sock.send(f"Muteaste a {objetivo_nombre}\n".encode())
                objetivo_sock.send("[Fuiste muteado, nadie puede escucharte]\n".encode())
            else:
                sock.send(f"Usuario '{objetivo_nombre}' no encontrado.\n".encode())

        elif clients[sock]["muted"]:
            sock.send("[Estás muteado, nadie puede escucharte]\n".encode())

        else:
            message = f"[{timestamp()}] {name}: {text}\n"
            broadcast(message, sender=sock)
            login(message.strip())

    except (ConnectionResetError, OSError):
        disconnect(sock, motive="caída inesperada")

# ---------- Funcion Main ----------
def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen()
    server_sock.setblocking(False)
    sel.register(server_sock, selectors.EVENT_READ, data="server")

    if previous_state:
        nombres = list(previous_state.keys())
        print(f"Servidor escuchando en {PORT}... (sesión previa con: {', '.join(nombres)})")
    else:
        print(f"Servidor escuchando en {PORT}...")

    try:
        while True:
            for key, _ in sel.select(timeout=1):
                if key.data == "server":
                    accept_client(key.fileobj)
                else:
                    manage_client(key.fileobj)
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        save_state()
        sel.close()
        server_sock.close()
        log_file.close()

if __name__ == "__main__":
    main()