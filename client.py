# ---------- Importacion de Librerias ----------
import socket # Permite crear conexiones de red
import time   
from threading import Thread # Permite ejecutar varias cosas al mismmo tienmpo
# ---------- Definicion de Constantes ----------
HOST = '127.0.0.1' # Localhost
PORT = 12345       
BUFFER = 4096      # Bytes = 4KB
MAX_RETRIES = 3
# ---------- Funcion Reintentos ----------
def connect_retries():
    for attempt in range(1, MAX_RETRIES + 1): # Bucle desde 1 hasta MAX_RETRIES
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # Crea el socket
            sock.connect((HOST, PORT))
            print("Conectado al servidor.")
            return sock # Devuelve el socket TCP IPv4 conectado
        except (ConnectionRefusedError, OSError):
            print(f"Intento {attempt} fallido. Reintentando en 3s...")
            time.sleep(3) # Pausa el programa 3s
    return None
# ---------- Funcion Recepcion de Mensajes ----------
def receive_messages(sock):
    while True:
        try:
            data = sock.recv(BUFFER)  # Recive datos del servidor 
            if not data:
                print("\n[Servidor cerro la conexion]")
                sock.close()
                break
            print(data.decode("utf-8"))  # Convierte bytes a string
        except (ConnectionResetError, OSError):
            print("\n[Conexion perdida con el servidor]")
            sock.close()  # Cierra el socket
            break
# ---------- Funcion Envio de Mensajes ----------
def send_messages(sock):
    while True:
        try:
            msg = input()
            if not msg:
                continue
            sock.send(msg.encode("utf-8")) # Envia el mensaje al servidor

            if msg == "/exit":
                print("Saliendo...")
                sock.close()
                break
        except (BrokenPipeError, OSError):
            print("[No se pudo enviar. Conexion rota]")
            break
        except KeyboardInterrupt:
            sock.send("/exit".encode("utf-8")) # Se envia el comando de salida al servidor
            sock.close()
            break
# ----------Funcion Main ----------
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