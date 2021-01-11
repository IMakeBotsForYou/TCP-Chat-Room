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


COMMAND_PREFIX = "/"


def handle_command(msg, client):
    args = msg.strip().split(" ")
    print(args)
    command = args[0][1:]
    if command == "nick" or command == "nickname":
        if len(args) > 1:
            print(f'|{"".join(args[1:])[1:]}|')
            prev_name = clients[client]
            clients[client] = "".join(args[1:])[1:]
            broadcast("{System} " + f'{prev_name} changed to {clients[client]}'.encode())
            return "{System} Nickname Updated.".encode()
        else:
            return ("{System} " + "Invalid Nickname").encode()

    # Currently online users
    if command == "current" or command == "online":
        return ("{System} " + str(len(clients)) + ' users online, ' + ' | '.join(clients.values())).encode()
    return "Invalid Command".encode()


def handle_client(client):  # Takes client socket as argument.
    """Handles a single client connection."""

    try:
        name = client.recv(BUFSIZ).decode()
    except ConnectionResetError:  # 10054
        print("error")
    else:
        connection_working = True
        welcome = "{System} " + 'Welcome %s! If you ever want to quit, type {quit} to exit.' % name
        client.send(welcome.encode())
        msg = "{System} " + "%s has joined the chat!" % name
        broadcast(msg.encode())
        clients[client] = name

        while True:
            try:
                msg = client.recv(BUFSIZ)
            except ConnectionResetError:  # 10054
                connection_working = False
            if connection_working and msg != "quit()".encode():
                if chr(msg[0]).encode() == COMMAND_PREFIX.encode():
                    print(f'Command executed by {clients[client]}, {str(msg)}')
                    client.send(handle_command(msg.decode(), client))
                else:
                    broadcast(msg, clients[client] + ": ")
            else:
                try:
                    client.send("quit()".encode())
                except ConnectionResetError:  # 10054
                    connection_working = False
                client.close()
                del clients[client]
                broadcast(("{System} " + "%s has left the chat." % name).encode())
                break


def broadcast(msg, prefix=""):  # prefix is for name identification.
    """Broadcasts a message to all the clients."""

    for sock in clients:
        try:
            sock.send(prefix.encode() + msg)
        except ConnectionResetError:  # 10054
            pass


HOST = ""
PORT = 45000
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
