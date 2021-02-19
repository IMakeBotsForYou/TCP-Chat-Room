"""Server for multi-threaded (asynchronous) chat application."""
from re import search
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
import requests as req
import time

KEY = [0]
last_update = 0
server_up = [True]


def accept_incoming_connections():
    """Sets up handling for incoming clients."""
    while server_up[0]:
        try:
            client, client_address = SERVER.accept()
            print(f"{client_address} has connected.")
            client.send("Greetings from the cave! Now type your name and press enter!\n".encode() +
                        "After you login, Enter /help or /commands to see the command list!".encode())
            addresses[client] = client_address
            Thread(target=handle_client, args=(client,)).start()
            print(f"Starting thread for {client_address}")

        except OSError:
            close_server()
            break


usage = {
    "nick": "/nick <new name>: Rename Yourself!",
    "nickname": "/nickname <new name>: Rename Yourself!",
    "w": "/w <name>: whisper to someone",
    "whisper": "/whisper <name>: whisper to someone",
    "online": "/online: show who's online!",
    "current": "current: show who's online!",
    "login": "/login <password> Try logging in as admin!",
    "block": "/block <username> You can't see a users messages anymore.\nTo revert, do /unblock <username>",
    "kick": "admin_/kick <username>: kicks a user",
    "ban": "admin_/ban <username>: bans a user",

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


def retrieve_key(force=False):
    """
    :param force: Forces the key update.
    This retrieves key from the heroku key api.
    """
    # I made a heroku app, which updates the key every minute.
    global last_update
    current_time = int(time.time()) * 1000
    if current_time - last_update > 60_000 or force:  # Update time for key
        data = req.get('https://get-api-key-2021.herokuapp.com/').json()
        KEY[0] = data['code']
        last_update = data['last_time']


def kick(client, delete=True, cl=False, message=True, custom=""):
    """
    :param client: The client being kicked/removed
    :param delete: Delete the client from the client list
    :param cl:  The server is being closed, so no need to say who left.
    :param message: Do we tell them they're kicked or no?
    :param custom: Custom kick message
    Kicks a user.
    """
    if message:
        if custom == "":
            client.send("{System} Kicked".encode())
        else:
            client.send(("{System} Kicked. Reason: " + custom).encode())
    if not cl:
        broadcast(("{System} " + "%s has left the chat." % clients[client][0]).encode())
    if delete:
        print(f"Deleted {clients[client]}")
        del clients[client]
        del addresses[client]
        print(f"{len(clients.values())} Users remaining")
    client.send("Kindly, leave".encode())


def close_server():
    # Close the server, kicking everyone

    for x in clients:
        try:
            kick(x, False, True)
        except OSError:
            pass
    lst = list(clients.keys()).copy()
    for x in lst:
        clients.pop(x, None)
    server_up[0] = False
    SERVER.close()


def encode(txt, key):
    return ''.join([chr(ord(a) ^ key) for a in txt])


def handle_command(msg, client):
    """
    :param msg: The message
    :param client: The client being handled.
    If the user has sent a command, instead of a normal message -
    we need to handle it properly.
    """

    print(f'Client {clients[client][0]}, {"is" if clients[client][1] else "is not"} an admin.')
    print(f'They have executed the command {msg} ({msg.strip().split(" ")})')
    # For me to know what you're up to.

    # split command into args
    args = msg.strip().split(" ")
    args = list(filter(None, args))
    # first arg is the command name, after the '/'
    command = args[0][1:]

    '''
    User is dumb
    '''
    print(args)
    if args[0].find("usage_") == 1:
        msg = msg[len(COMMAND_PREFIX) + len("usage_"):]
        command = msg.split(" ")[0]
        if not clients[client][1]:  # if not admin, send only valid commands
            if usage[command][:6] == "admin_" or command not in usage:
                return "{System} Usage: ".encode() + "Not a valid command".encode()
            return "{System} Usage: ".encode() + usage[command].encode()

    elif clients[client][1]:
        # Admin commands
        if command == "close" or command == "end":
            try:
                server_up[0] = False
                close_server()
            except OSError:
                pass

        if command == "kick":
            recipient_name = args[1]
            # Are we kicking an ip or a name?
            if search(r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?\.){4}"[:-1], recipient_name):
                recipient = get_client(recipient_name, True)
            else:
                recipient = get_client(recipient_name)

            if recipient != "invalid":
                if len(args) > 2:
                    kick_msg = ' '.join(args[2:])
                else:
                    kick_msg = ""
                kick(recipient, message=True, custom=kick_msg, cl=True)
                # it's gonna say that he left anyway so cl is true here

                mess1 = "{System} ".encode() + f"Update user_num,{len(clients.values())}".encode()
                mess2 = "{System} ".encode() + f"Update members{'+'.join([x[0] for x in clients.values()])}".encode()
                broadcast(mess1 + mess2)

                broadcast("{System} ".encode() + f"{recipient_name} was kicked by {clients[client][0]}"
                                                 f"{'' if kick_msg == '' else ' for ' + kick_msg}".encode())
                return "don't".encode()
            else:
                return f'That recipient is not connected.'.encode()


    '''
    Logging in as admin
    We need to check if user is already an admin or not,
    and receive the password.
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

            retrieve_key()
            print(''.join(args[1:]), KEY[0])
            passw = encode(''.join(args[1:]), KEY[0])
            clients[client] = [clients[client][0], passw == admin_password]
            print('Logged in!' if passw == admin_password else "Login failed.")
            return 'Logged in!'.encode() if passw == admin_password else "Login failed.".encode()

    if command == "w" or command == "whisper":
        recipient_name = args[1]
        recipient = get_client(recipient_name)
        if recipient == client:
            return "You can't message yourself, dummy".encode()

        if recipient != "invalid":
            recipient.send(("Message from " + clients[client][0] + ": " + ' '.join(args[2:])).encode())
        else:
            return f'That recipient is not connected.'.encode()

        return f'Direct message to: {recipient_name} - {" ".join(args[2:])}'.encode()

    if command == "help" or command == "commands":
        return (command_list + admin_cmd_list).encode() if clients[client][1] else command_list.encode()

    if command == "nick" or command == "nickname":
        if len(args) > 1:
            recipient_name = args[1]
            banned_keywords = ["{System}", "@", ":", COMMAND_PREFIX]

            if len([x for x in banned_keywords if recipient_name.find(x) != -1]) != 0:
                return "Invalid nickname".encode()

            recipient = get_client(recipient_name)

            if recipient == "invalid":
                prev_name = clients[client][0]
                clients[client][0] = "_".join(word for word in args[1:] if word != "")

                mess1 = "{System} ".encode() + f"Update user_num,{len(clients.values())}".encode()
                mess2 = "{System} ".encode() + f"Update members{'+'.join([x[0] for x in clients.values()])}".encode()

                broadcast(mess1 + mess2)

                broadcast(("{System} " + f'{prev_name} changed to {clients[client][0]}\n').encode())
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
        banned_words = ["{System}", "@", ":", COMMAND_PREFIX] + [x[0] for x in clients.values()]
        while len([key_word for key_word in banned_words if name.find(key_word) != -1]) != 0:
            print(name, [key_word for key_word in banned_words if name.find(key_word) != -1])
            client.send("Invalid nickname, the name is either taken\nor it has an illegal character".encode())
            name = client.recv(BUFSIZ).decode()

    except ConnectionResetError:  # 10054
        print("Client error'd out.")
        del addresses[client]
    else:
        connection_working = True
        print("Handling client")
        welcome = "{System} " + 'Welcome %s! If you ever want to quit, type quit() or press [X] to exit.' % name
        client.send(welcome.encode())
        msg = "{System} " + "%s has joined the chat!" % name
        broadcast(msg.encode())
        clients[client] = [name.replace(" ", "_"), False]

        mess1 = "{System} ".encode() + f"Update user_num,{len(clients.values())}".encode()
        mess2 = "{System} ".encode() + f"Update members{'+'.join([x[0] for x in clients.values()])}".encode()

        broadcast(mess1 + mess2)

        while server_up[0]:
            print(server_up)
            try:
                msg = client.recv(BUFSIZ)
            except ConnectionResetError:  # 10054
                connection_working = False
            except ConnectionAbortedError:
                connection_working = False

            if connection_working and msg != "quit()".encode():
                if chr(msg[0]).encode() == COMMAND_PREFIX.encode():
                    client.send("{System} ".encode() + handle_command(msg.decode(), client))
                else:
                    broadcast(msg, clients[client][0] + ": ")
            else:
                try:
                    kick(client, message=False, delete=True, cl=False)
                except ConnectionResetError:  # 10054
                    print("Client did an oopsie")
                    del clients[client]
                except OSError:
                    print("Client did an oopsie")
                    del clients[client]
                except KeyError:
                    print(f"Tried deleting {client}, but they were already gone. (line 301)")
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
