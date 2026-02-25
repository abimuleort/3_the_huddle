# ---------- Importacion de Librerias ----------
import selectors # Alternativa de threads. Permite manejar multiples conexiones
import socket
import datetime 
# ---------- Definicion de Constantes ----------
HOST = "0.0.0.0" # Acepta conexiones desde cualquier IP
PORT = 12345
BUFFER = 4096 # Max Bytes 

clients = {} # Guarda todos los clientes conectados 
sel = selectors.DefaultSelector() # Crea el selector principal
log_file = open("chat.log", "a", encoding="utf-8") # Guarda historial

# ---------- Funcion Tiempo ----------
def timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S") # Obtiene hora actual

# ---------- Funcion Login ----------
def login(message):
    log_file.write(message + "\n") # Escribe el mensaje en el archivo
    log_file.flush() # Fuerza escritura inmediata en el disco

# ---------- Funcion Broadcast ----------
def broadcast(message, sender=None):
    muertos = [] # Lista de sockets muertos
    for sock in clients:
        if sock != sender: # No se reenvia al emisor
            try:
                sock.send(message.encode("utf-8"))
            except Exception:
                muertos.append(sock) # Si falla, el socket esta muerto
    for sock in muertos:
        disconnect(sock, motive="socket muerto en broadcast") # Desconecta 

# ---------- Funcion Desconexion ----------
def disconnect(sock, motive="desconexión"):
    if sock in clients:
        name = clients[sock]["name"]
        message = f"[{timestamp()}] *** {name} abandonó el chat ({motive}) ***"

        del clients[sock] # Elimina al cliente del diccionario
        try:
            sel.unregister(sock) # Elimina al socket del selector
        except Exception:
            pass
        try:
            sock.close() # Cierra la conexion 
        except Exception:
            pass

        broadcast(message, sender=None)
        login(message)
        print(f"Conexión cerrada: {name} — {motive}")

# ---------- Funcion Aceptar Cliente ----------
def accept_client(server_sock):
    conn, addr = server_sock.accept() # Acepta nueva conexion
    conn.setblocking(True) # Bloquea para pedir nommbre de usuario

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

    conn.setblocking(False) # Desbloquea para manejo con selector

    clients[conn] = {
        "name": name,
        "addr": addr,
        "muted": False
    }

    sel.register(conn, selectors.EVENT_READ, data="client") # Registra socket en selector

    mensaje_bienvenida = f"[{timestamp()}] *** {name} se unió al chat ***\n"
    broadcast(mensaje_bienvenida, sender=None)
    login(mensaje_bienvenida.strip())
    print(mensaje_bienvenida.strip())

# ---------- Funcion Manejo del Cliente ----------
def manage_client(sock):
    try:
        data = sock.recv(BUFFER) # Recibe datos

        if not data: # Cliente desconectado
            disconnect(sock, motive="desconexión limpia")
            return

        text = data.decode("utf-8").strip()
        name = clients[sock]["name"]

        if text == "/exit":
            disconnect(sock, motive="salida voluntaria")

        elif text.startswith("/mute "):
            objetivo_nombre = text[6:].lstrip("@").strip()
            objetivo_sock = next( # Busca socket del usuario
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

            message = f"[{timestamp()}] {name}: {text}\n" # Crea el mensaje
            broadcast(message, sender=sock)
            login(message.strip())

    except (ConnectionResetError, OSError):
        disconnect(sock, motivo="caída inesperada")

# ---------- Funcion Main ----------
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