import socket
import time
from threading import Thread

HOST = '127.0.0.1'
PORT = 12345
BUFFER = 4096
MAX_RETRIES = 3

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

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(BUFFER)
            if not data:
                print("\n[Servidor cerro la conexion]")
                sock.close()
                break
            print(data.decode("utf-8"))
        except (ConnectionResetError, OSError):
            print("\n[Conexion perdida con el servidor]")
            sock.close()
            break

def send_messages(sock):
    while True:
        try:
            msg = input()
            if not msg:
                continue
            sock.send(msg.encode("utf-8"))

            if msg == "/exit":
                print("Saliendo...")
                sock.close()
                break
        except (BrokenPipeError, OSError):
            print("[No se pudo enviar. Conexion rota]")
            break
        except KeyboardInterrupt:
            sock.send("/exit".encode("utf-8"))
            sock.close()
            break

def main():
    sock = connect_retries()
    if sock is None:
        print("No se pudo conectar al servidor. Saliendo...")
        return

    thread_receive = Thread(target=receive_messages, args=(sock,))
    thread_receive.daemon = True
    thread_receive.start()
    send_messages(sock)

if __name__ == "__main__":
    main()  