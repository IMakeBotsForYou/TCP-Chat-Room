"""Server for multithreaded (asynchronous) chat application."""
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread


def accept_incoming_connections():
    """Sets up handling for incoming clients."""
    while True:
        client, client_address = SERVER.accept()
        print("%s:%s has connected." % client_address)
        client.send("Greetings from the cave! Now type your name and press enter!".encode())
        addresses[client] = client_address
        Thread(target=handle_client, args=(client,)).start()


def handle_client(client):  # Takes client socket as argument.
    """Handles a single client connection."""

    try:
        name = client.recv(BUFSIZ).decode()
    except ConnectionResetError:  # 10054
        pass
    else:
        connection_working = True
        welcome = 'Welcome %s! If you ever want to quit, type {quit} to exit.' % name
        client.send(welcome.encode())
        msg = "%s has joined the chat!" % name
        broadcast(msg.encode())
        clients[client] = name

        while True:
            try:
                msg = client.recv(BUFSIZ)
            except ConnectionResetError:  # 10054
                connection_working = False
            if connection_working and msg != "{quit}".encode():
                broadcast(msg, name + ": ")
            else:
                try:
                    client.send("{quit}".encode())
                except ConnectionResetError:  # 10054
                    connection_working = False
                client.close()
                del clients[client]
                broadcast(("%s has left the chat." % name).encode())
                break


def broadcast(msg, prefix=""):  # prefix is for name identification.
    """Broadcasts a message to all the clients."""

    for sock in clients:
        try:
            sock.send(prefix.encode() + msg)
        except ConnectionResetError:  # 10054
            pass




HOST = ""
PORT = 21567
BUFSIZ = 1024
ADDR = (HOST, PORT)

clients = {}
addresses = {}

SERVER = socket(AF_INET, SOCK_STREAM)
SERVER.bind(ADDR)

SERVER.listen(5)
print("Waiting for connection...")
ACCEPT_THREAD = Thread(target=accept_incoming_connections)
ACCEPT_THREAD.start()
ACCEPT_THREAD.join()
SERVER.close()
