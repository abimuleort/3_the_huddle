# ---------- Importacion de Librerias ----------
import socket
import time
from threading import Thread, Event # MODIFIED Se agrega Event para señalizar desconexión

# ---------- Definicion de Constantes ----------
HOST = '127.0.0.1'
PORT = 12345
BUFFER = 4096
MAX_RETRIES = 10 # MODIFIED se aumenta para dar más tiempo al servidor a levantar
RETRY_DELAY = 3  # MODIFIED Constante explícita para el tiempo entre reintentos

# ---------- Estado del Cliente ----------
saved_name = None           # Nombre guardado para reconexion automatica
disconnected_event = Event() # NEW LINE Señal que indica que se perdió la conexión con el servidor

# ---------- Funcion Reintentos ----------
def connect_retries():
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))
            return sock # MODIFIED Ya no imprime "Conectado"; se hace en main()
        except (ConnectionRefusedError, OSError):
            print(f"\r[Reconectando... intento {attempt}/{MAX_RETRIES}]", end="", flush=True)
            time.sleep(RETRY_DELAY)
    return None

# ---------- Funcion Recepcion de Mensajes ----------
def receive_messages(sock):
    while True:
        try:
            data = sock.recv(BUFFER)
            if not data:
                print("\n[Servidor cerró la conexión. Presioná Enter para reconectar...]")
                break
            print(data.decode("utf-8"), end="", flush=True)
        except (ConnectionResetError, OSError):
            print("\n[Conexión perdida. Presioná Enter para reconectar...]")
            break
    sock.close()
    disconnected_event.set()  # Señala al hilo principal que se perdió la conexión

# ---------- Funcion Envio de Mensajes ----------
def send_messages(sock):
    while True:
        try:
            msg = input()
            # Si ya nos desconectamos, el Enter del usuario activa la reconexión
            if disconnected_event.is_set():
                break
            if not msg:
                continue
            sock.send(msg.encode("utf-8"))
            if msg == "/exit":
                print("Saliendo...")
                disconnected_event.set()
                break
        except (BrokenPipeError, OSError):
            print("[No se pudo enviar. Conexión rota]")
            break
        except KeyboardInterrupt:
            try:
                sock.send("/exit".encode("utf-8"))
            except Exception:
                pass
            disconnected_event.set()
            break

# ---------- Funcion Handshake ----------
def handshake(sock):
    global saved_name
    try:
        # Recibir prompt del servidor
        prompt = sock.recv(BUFFER).decode("utf-8")

        if saved_name:
            # Reconexion: enviar nombre guardado sin preguntar al usuario
            sock.send(saved_name.encode("utf-8"))
            name = saved_name
        else:
            # Primera conexion: pedir nombre
            name = input(prompt).strip()
            if not name:
                name = "Anonimo"
            sock.send(name.encode("utf-8"))

        # Leer confirmacion del servidor (OK_RECONNECT o OK_NEW)
        confirmation = sock.recv(BUFFER).decode("utf-8").strip()

        if confirmation.startswith("OK_RECONNECT:"):
            confirmed_name = confirmation[len("OK_RECONNECT:"):]
            print(f"[Reconectado al servidor como '{confirmed_name}']")
        elif confirmation.startswith("OK_NEW:"):
            confirmed_name = confirmation[len("OK_NEW:"):]
            # No imprimir nada extra en primera conexion, es lo normal
        else:
            confirmed_name = name  # Fallback

        saved_name = confirmed_name
        return confirmed_name

    except (ConnectionResetError, OSError) as e:
        print(f"[Error durante el handshake: {e}]")
        return None

# ---------- Funcion Main ----------
def main():
    global saved_name

    # --- Primera conexion ---
    print(f"Conectando a {HOST}:{PORT}...")
    sock = connect_retries()
    if sock is None:
        print("\nNo se pudo conectar al servidor. Saliendo...")
        return

    print("Conectado.")
    name = handshake(sock)
    if name is None:
        sock.close()
        return

    # --- Bucle principal: chat + reconexion automatica ---
    while True:
        disconnected_event.clear()

        thread_receive = Thread(target=receive_messages, args=(sock,), daemon=True)
        thread_receive.start()

        send_messages(sock)  # Bloquea hasta que se mande /exit o se rompa la conexion

        thread_receive.join(timeout=2)

        # Si fue /exit intencional, salir del todo
        if not saved_name:
            break

        # Verificar si el usuario quiere salir o reconectar
        # (el Enter ya fue presionado en send_messages al detectar desconexion)
        if not disconnected_event.is_set():
            break

        # Intentar reconectar automaticamente
        print(f"[Intentando reconectar como '{saved_name}'...]")
        sock = connect_retries()
        if sock is None:
            print("\nNo se pudo reconectar. Saliendo...")
            break

        print()  # Salto de linea tras los mensajes de reintento
        name = handshake(sock)
        if name is None:
            print("Error en reconexión. Saliendo...")
            break
        # Continua el bucle con el nuevo socket

if __name__ == "__main__":
    main()