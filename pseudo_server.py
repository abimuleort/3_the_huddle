'''
PROGRAMA servidor_chat:

  CONSTANTES:
    HOST = '0.0.0.0'
    PORT = 12345
    BUFFER = 4096

  ESTRUCTURAS:
    clientes = {}        # socket → {nombre, addr, muted: bool}
    log_file = abrir("chat.log", modo append)
    sel = crear_selector()

  ─────────────────────────────────────────
  FUNCIÓN main():

    server_sock = crear_socket(TCP)
    server_sock.setsockopt(SO_REUSEADDR)
    server_sock.bind(HOST, PORT)
    server_sock.listen()
    server_sock.setblocking(False)

    sel.register(server_sock, LEER, data="server")

    imprimir "Servidor escuchando en PORT..."

    INTENTAR:
      LOOP infinito:
        eventos = sel.select(timeout=1)

        PARA cada (key, mask) en eventos:
          SI key.data == "server":
            aceptar_cliente(key.fileobj)
          SINO:
            manejar_cliente(key.fileobj)

    EXCEPTO KeyboardInterrupt:
      imprimir "Servidor detenido."

    FINALMENTE:
      sel.cerrar()
      server_sock.cerrar()
      log_file.cerrar()

  ─────────────────────────────────────────
  FUNCIÓN aceptar_cliente(server_sock):

    conn, addr = server_sock.accept()
    conn.setblocking(True)      # bloqueante solo durante el handshake

    INTENTAR:
      conn.send("Ingresá tu nombre de usuario: ")
      conn.settimeout(30)
      nombre = conn.recv(BUFFER).decodificar().strip()

      SI nombre está vacío:
        nombre = "Anonimo_" + str(addr.port)

    EXCEPTO timeout:
      nombre = "Anonimo_" + str(addr.port)

    EXCEPTO (ConnectionResetError, OSError):
      conn.cerrar()
      RETORNAR

    conn.setblocking(False)     # vuelve a no-bloqueante antes de registrar

    clientes[conn] = {
      "nombre": nombre,
      "addr":   addr,
      "muted":  False
    }

    sel.register(conn, LEER, data="client")

    mensaje_bienvenida = "[{timestamp()}] *** {nombre} se unió al chat ***\n"
    broadcast(mensaje_bienvenida, remitente=None)
    loguear(mensaje_bienvenida)
    imprimir mensaje_bienvenida

  ─────────────────────────────────────────
  FUNCIÓN manejar_cliente(sock):

    INTENTAR:
      data = sock.recv(BUFFER)

      SI data está vacía:
        desconectar(sock, motivo="desconexión limpia")
        RETORNAR

      texto = data.decodificar().strip()
      nombre = clientes[sock].nombre

      SI texto == "/exit":
        desconectar(sock, motivo="salida voluntaria")

      SINO SI texto empieza con "/mute ":
        objetivo_nombre = texto.eliminar_prefijo("/mute ").eliminar_prefijo("@").strip()
        objetivo_sock = buscar_cliente_por_nombre(objetivo_nombre)

        SI objetivo_sock existe:
          clientes[objetivo_sock].muted = True
          sock.send("Muteaste a {objetivo_nombre}\n")
        SINO:
          sock.send("Usuario '{objetivo_nombre}' no encontrado.\n")

      SINO:
        SI clientes[sock].muted:
          sock.send("[Estás muteado, nadie te escucha]\n")
          RETORNAR

        mensaje = "[{timestamp()}] {nombre}: {texto}\n"
        broadcast(mensaje, remitente=sock)
        loguear(mensaje)

    EXCEPTO (ConnectionResetError, OSError):
      desconectar(sock, motivo="caída inesperada")

  ─────────────────────────────────────────
  FUNCIÓN broadcast(mensaje, remitente):

    muertos = []

    PARA cada sock en clientes:
      SI sock != remitente:
        INTENTAR:
          sock.send(mensaje.codificar())
        EXCEPTO:
          muertos.agregar(sock)

    PARA cada sock en muertos:
      desconectar(sock, motivo="socket muerto en broadcast")

  ─────────────────────────────────────────
  FUNCIÓN desconectar(sock, motivo):

    SI sock en clientes:
      nombre  = clientes[sock].nombre
      mensaje = "[{timestamp()}] *** {nombre} abandonó el chat ({motivo}) ***"

      del clientes[sock]

      INTENTAR: sel.unregister(sock)
      INTENTAR: sock.cerrar()

      broadcast(mensaje, remitente=None)
      loguear(mensaje)
      imprimir "Conexión cerrada: {nombre} — {motivo}"

  ─────────────────────────────────────────
  FUNCIÓN buscar_cliente_por_nombre(nombre_buscado):

    PARA cada (sock, info) en clientes:
      SI info.nombre == nombre_buscado:
        RETORNAR sock

    RETORNAR None

  ─────────────────────────────────────────
  FUNCIÓN loguear(mensaje):
    log_file.escribir(mensaje)
    log_file.flush()

  FUNCIÓN timestamp():
    RETORNAR hora_actual.formato("HH:MM:SS")
'''