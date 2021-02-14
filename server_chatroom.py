"""Server for multi-threaded (asynchronous) chat application."""
from re import search
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
import requests as req


def accept_incoming_connections():
    """Sets up handling for incoming clients."""
    while True:
        client, client_address = SERVER.accept()
        print(client)
        print(f"{client_address} has connected.")
        client.send("Greetings from the cave! Now type your name and press enter!\n".encode() +
                    "After you login, Enter /help or /commands to see the command list!".encode())
        addresses[client] = client_address
        Thread(target=handle_client, args=(client,)).start()
        print(f"Starting thread for {client_address}")


usage = {
    "nick": "/nick <new name>: Rename Yourself!",
    "nickname": "/nickname <new name>: Rename Yourself!",
    "w": "/w <name>: whisper to someone",
    "whisper": "/whisper <name>: whisper to someone",
    "online": "/online: show who's online!",
    "current": "current: show who's online!",
    "login": "/login <password> Try logging in as admin!"
}

command_list = "Command List:\n" + \
               "/nick <new name>: Rename Yourself!\n" + \
               "/whisper <name>: whisper to someone\n" + \
               "/online: show who's online!\n" + \
               "/login <password>: Try logging in as admin\n"

admin_cmd_list = "/end, or /close -> closes server.\n" + \
                 "/boot or /kick -> kicks a user by username\n"

admin_password = "danistheking"

COMMAND_PREFIX = "/"


def get_client(val, ip=False):
    """
    :param val: name to search
    :param ip: Search by ip? (default off)
    """
    if ip:
        for key, value in addresses.items():
            if val == value[0]:
                return key
    else:
        for key, value in clients.items():
            if val == value[0]:
                return key
    return "invalid"


def retrieve_key(client):
    """
    Asks the client for its current key.
    :param client: The client being asked.
    """
    client.send(("What is the key?".encode()))
    return int(client.recv(BUFSIZ).decode())


def kick(client, delete=True, cl=False, message=True):
    """
    :param client: The client being kicked/removed
    :param delete: Delete the client from the client list
    :param cl:  The server is being closed, so no need to say who left.
    :param message: Do we tell them they're kicked or no?
    Kicks a user.
    """
    if message:
        client.send("{System} Kicked".encode())
    if not cl:
        broadcast(("{System} " + "%s has left the chat." % clients[client][0]).encode())
    if delete:
        print(f"Deleted {clients[client]}")
        del clients[client]
    client.send("Kindly, leave".encode())


def close_server():
    # If admin, close
    for x in clients:
        try:
            kick(x, False, True)
        except OSError:
            pass
    lst = list(clients.keys()).copy()
    for x in lst:
        clients.pop(x, None)
    exit(0)
    quit(0)


def handle_command(msg, client):
    """
    :param msg: The message
    :param client: The client being handled.
    If the user has sent a command, instead of a normal message -
    we need to handle it properly.
    """

    print(f'Client {clients[client][0]}, {"is" if clients[client][1] else "is not"} an admin.')
    print(f'They have executed the command {msg}')
    # For me to know what you're up to.

    # split command into args
    args = msg.strip().split(" ")
    # first arg is the command name, after the '/'
    command = args[0][1:]

    '''
    User is dumb
    '''
    print(args)
    if args[0].find("usage_") == 1:
        msg = msg[len(COMMAND_PREFIX)+len("usage_"):]
        command = msg.split(" ")[0]
        print(command)
        return "{System} Usage: ".encode() + usage[command].encode()

    '''
    Admin commands
    '''
    if clients[client][1]:
        if command == "kick":
            recipient_name = ''.join([chr(ord(a) ^ retrieve_key(client)) for a in ''.join(args[1:])])

            # Are we kicking an ip or a name?
            if search(r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?\.){4}"[:-1], recipient_name):
                recipient = get_client(recipient_name, True)
            else:
                recipient = get_client(recipient_name)

            if recipient != "invalid":
                kick(recipient)
            else:
                return f'That recipient is not connected.'.encode()

    '''
    Regular commands
    '''
    if command == "close" or command == "end":
        if clients[client][1]:
            close_server()
        else:
            return 'You can\'t do that!'.encode()

    '''
    Logging in as admin
    We need to check if user is already an adimn or not,
    and recieve the password.
    '''
    if command == "login":
        if clients[client][1]:
            client.send(("{System} " "You're already admin! Want to log out? y/N".encode()))
            login = client.recv(BUFSIZ).decode().lower()
            if login == "y" or login == "yes":
                clients[client][1] = False
            else:
                return "Canceled.".encode()
        else:
            print(f"Logging {clients[client][0]} in")
            key = req.get("https://get-api-key-2021.herokuapp.com/").json()['code']

            passw = ''.join([chr(ord(a) ^ key) for a in ''.join(args[1:])])
            clients[client] = [clients[client][0], passw == admin_password]

            print('Logged in!' if passw == admin_password else "Login failed.")
            return 'Logged in!'.encode() if passw == admin_password else "Login failed.".encode()

    if command == "w" or command == "whisper":
        recipient_name = args[1]
        recipient = get_client(recipient_name)
        # if recipient == client:
        #     return "You can't message yourself, dummy".encode()

        if recipient != "invalid":
            recipient.send(("{System} Message from " + clients[client][0] + ": " + ' '.join(args[2:])).encode())
        else:
            return f'That recipient is not connected.'.encode()

        return f'Direct message to: {recipient_name} - {" ".join(args[2:])}'.encode()

    if command == "help" or command == "commands":
        return (command_list + admin_cmd_list).encode() if clients[client][1] else command_list.encode()

    if command == "nick" or command == "nickname":
        if len(args) > 1:

            recipient_name = args[1]
            recipient = get_client(recipient_name)
            print(recipient)

            if recipient == "invalid":
                prev_name = clients[client][0]
                clients[client][0] = "_".join(word for word in args[1:] if word != "")
                broadcast(("{System} " + f'{prev_name} changed to {clients[client][0]}').encode())
                return "Nickname Updated.".encode()
            else:
                return f'That name is taken.'.encode()
        else:
            return "Must enter a nickname.".encode()

    # Currently online users
    if command == "current" or command == "online":
        return (str(len(clients)) + ' users online, ').encode() + ' | '.join([x[0] for x in clients.values()]).encode()
    return "Invalid Command".encode()


def handle_client(client):  # Takes client socket as argument.
    """Handles a single client connection."""

    try:
        name = client.recv(BUFSIZ).decode()

    except ConnectionResetError:  # 10054
        print("Client error'd out.")
    else:
        connection_working = True
        print("Handling client")
        welcome = "{System} " + 'Welcome %s! If you ever want to quit, type quit() or press [X] to exit.' % name
        client.send(welcome.encode())
        msg = "{System} " + "%s has joined the chat!" % name
        broadcast(msg.encode())
        clients[client] = [name.replace(" ", "_"), False]

        mess1 = "{System} ".encode() + f"Update user_num,{len(addresses.keys())}".encode()
        mess2 = "{System} ".encode() + f"Update members{'+'.join([x[0] for x in clients.values()])}".encode()

        broadcast(mess1+mess2)


        while True:
            try:
                msg = client.recv(BUFSIZ)
            except ConnectionResetError:  # 10054
                connection_working = False
                del clients[client]
            except ConnectionAbortedError:
                connection_working = False
                del clients[client]

            if connection_working and msg != "quit()".encode():
                if chr(msg[0]).encode() == COMMAND_PREFIX.encode():
                    print(f'Command executed by {clients[client][0]}, {str(msg.decode("utf8"))}')
                    client.send("{System} ".encode() + handle_command(msg.decode(), client))
                else:
                    broadcast(msg, clients[client][0] + ": ")
            else:
                try:
                    client.send("{System} Kindly, leave".encode())
                    kick(client, message=False, delete=False, cl=False)
                    del clients[client]
                except ConnectionResetError:  # 10054
                    connection_working = False
                    del clients[client]
                except OSError:
                    connection_working = False
                    del clients[client]
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
