'''
PROGRAMA cliente_chat:

  CONSTANTES:
    HOST = IP del servidor     # cambiar por IP local del café si aplica
    PORT = 12345
    BUFFER = 4096
    MAX_REINTENTOS = 3

  ─────────────────────────────────────────
  FUNCIÓN main():

    sock = conectar_con_reintentos()
    SI sock es None:
      imprimir "No se pudo conectar. Hasta la próxima."
      SALIR

    # Dos hilos: uno escucha, uno habla
    hilo_recibir = Thread(target=recibir_mensajes, args=(sock,))
    hilo_recibir.daemon = True    # muere si el main muere
    hilo_recibir.start()

    enviar_mensajes(sock)         # corre en el hilo principal

  ─────────────────────────────────────────
  FUNCIÓN conectar_con_reintentos():

    PARA intento en 1..MAX_REINTENTOS:
      INTENTAR:
        sock = crear_socket(TCP)
        sock.connect(HOST, PORT)
        imprimir "Conectado al servidor."
        RETORNAR sock

      EXCEPTO (ConnectionRefusedError, OSError):
        imprimir "Intento {intento} fallido. Reintentando en 3s..."
        esperar(3)

    RETORNAR None

  ─────────────────────────────────────────
  FUNCIÓN recibir_mensajes(sock):
    # Corre en su propio hilo — solo escucha

    LOOP:
      INTENTAR:
        data = sock.recv(BUFFER)

        SI data vacía:
          imprimir "\n[Servidor cerró la conexión]"
          sock.close()
          SALIR del loop

        imprimir data.decodificar()   # mostrar en terminal tal cual llega

      EXCEPTO (ConnectionResetError, OSError):
        imprimir "\n[Conexión perdida con el servidor]"
        sock.close()
        SALIR del loop

  ─────────────────────────────────────────
  FUNCIÓN enviar_mensajes(sock):
    # Corre en hilo principal — solo envía

    LOOP:
      INTENTAR:
        texto = input()              # bloqueante, espera que el user escriba

        SI texto vacío: CONTINUAR

        sock.send(texto.codificar())

        SI texto == "/exit":
          imprimir "Saliendo..."
          sock.close()
          SALIR del loop

      EXCEPTO (BrokenPipeError, OSError):
        imprimir "[No se pudo enviar. Conexión rota]"
        SALIR del loop

      EXCEPTO KeyboardInterrupt:    # Ctrl+C
        sock.send("/exit".codificar())
        sock.close()
        SALIR del loop
'''