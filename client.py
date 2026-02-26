# ---------- Importacion de Librerias ----------
import socket
import time
from threading import Thread

# ---------- Definicion de Constantes ----------
HOST = '127.0.0.1'
PORT = 12345
BUFFER = 4096
MAX_RETRIES = 3

# ---------- Funcion Reintentos ----------
def connect_retries():
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))
            print("Conectado al servidor.")
            return sock
        except (ConnectionRefusedError, OSError):
            print(f"Intento {attempt} fallido. Reintentando en 3s...")
            time.sleep(3)
    return None

# ---------- Funcion Recepcion de Mensajes ----------
def receive_messages(sock):
    while True:
        try:
            data = sock.recv(BUFFER)
            if not data:
                print("\n[Servidor cerró la conexión]")
                break
            print(data.decode("utf-8"), end="")
        except (ConnectionResetError, OSError):
            print("\n[Conexión perdida con el servidor]")
            break
    sock.close()

# ---------- Funcion Envio de Mensajes ----------
def send_messages(sock):
    while True:
        try:
            msg = input()
            if not msg:
                continue
            sock.send(msg.encode("utf-8"))
            if msg == "/exit":
                print("Saliendo...")
                break
        except (BrokenPipeError, OSError):
            print("[No se pudo enviar. Conexión rota]")
            break
        except KeyboardInterrupt:
            sock.send("/exit".encode("utf-8"))
            break
    sock.close()

# ---------- Funcion Main ----------
def main():
    sock = connect_retries()
    if sock is None:
        print("No se pudo conectar al servidor. Saliendo...")
        return

    # Recibe el prompt de nombre, lo muestra y envia la respuesta
    # antes de arrancar el hilo receptor para evitar mezcla en consola
    try:
        prompt = sock.recv(BUFFER).decode("utf-8")
        name = input(prompt).strip()
        sock.send(name.encode("utf-8"))
    except (ConnectionResetError, OSError):
        print("[Error durante el login]")
        sock.close()
        return

    thread_receive = Thread(target=receive_messages, args=(sock,), daemon=True)
    thread_receive.start()
    send_messages(sock)

if __name__ == "__main__":
    main()