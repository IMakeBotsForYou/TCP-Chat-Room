"""Server for multi-threaded (asynchronous) chat application."""
from re import search
from socket import AF_INET, socket, SOCK_STREAM, MSG_PEEK
from threading import Thread
import requests as req
import time

KEY = [0]
last_update = 0
server_up = [True]
cmd_prefix = "/"
colours = {
    "red": "dd0404",
    "pink": "ff6666",
    "low-yellow": "d9c000",
    "orange-warning": "D49B00",
    "low-green": "339966",
    "bright-green": "27DB03",
    "blue": "0066cc",
    "whisper-gray": "ab9aa0"
}


def msg_len(data):
    return str(len(data.encode())).zfill(3)


def accept_incoming_connections():
    """Sets up handling for incoming clients."""
    while server_up[0]:
        try:
            client, client_address = SERVER.accept()
            print(f"{client_address} has connected.")
            data = "Greetings from the cave! Now type your name and press enter!\n" \
                   "After you login, Enter /help or /commands to see the command list!"
            header = "SysCmd" + msg_len(data) + "NOBGCL" + "1"
            client.send((header + data + "000").encode())
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
    "color": "/color ",
    "kick": "admin_/kick <username>: kicks a user",
    "boot": "admin_/boot <username>: kicks a user",
    "logout": "admin_/logout: logs out of admin mode",
    "end": "admin_/end: Ends server lol",
    "close": "admin_/end: Ends server lol"
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
            data = "Kicked"
            header = "SysCmd" + msg_len(data) + colours['red'] + "0"
            client.send((data + header).encode())
        else:
            data = "Kicked. Reason: " + custom
            header = "SysCmd" + msg_len(data) + colours['red'] + "0"
            client.send((data + header).encode())
    if not cl:
        user = "%s has left the chat." % clients[client][0]
        length = msg_len(user)
        broadcast(f"SysCmd{length}NOBGCL1{user}000")
    if delete:
        print(f"Deleted {clients[client]}")
        del clients[client]
        del addresses[client]
        print(f"{len(clients.values())} Users remaining")
        # Type     Length   Colour  Display   Message
    client.send(("SysCmd" + "013" + "FFFFFF" + "0" + "Kindly, leave" + "000").encode())


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


def send_update(start_chain, end_chain):
    chain = "SysCmd" if start_chain else ""

    # No need for type because chain has already begun.
    data = f"Update user_num,{str(len(clients.values())).zfill(2)}"
    header = msg_len(data) + "FFFFFF" + "0"
    chain += header + data

    # No need for type because chain has already begun.
    data = f"Update members{'+'.join([x[0] for x in clients.values()])}"
    header = msg_len(data) + "FFFFFF" + "0"
    chain += header + data
    broadcast(chain)
    if end_chain:
        print("Updated with kill")
        broadcast("000")  # kill command chain


def handle_command(data, client):
    """
    :param data: The message
    :param client: The client being handled.
    If the user has sent a command, instead of a normal message -
    we need to handle it properly.
    """
    print(f'Client {clients[client][0]}, {"is" if clients[client][1] else "is not"} an admin.')
    print(f'They have executed the command {data} ({data.strip().split(" ")})')
    # For me to know what you're up to.

    # split command into args
    args = data.strip().split(" ")
    args = list(filter(None, args))
    # first arg is the command name, after the '/'
    command = args[0][len(cmd_prefix):]

    if args[0].find("usage_") == 1:
        data = data[len(cmd_prefix) + len("usage_"):]
        command = data.split(" ")[0]
        if not clients[client][1]:  # if not admin, send only valid commands
            if usage[command][:6] == "admin_" or command not in usage:
                return "Usage: Not a valid command", "AA0404"
            return f"Usage: {usage[command]}", "NOBGCL"

    if command in ["w", "whisper"]:
        recipient_name = args[1]
        recipient = get_client(recipient_name)
        if recipient == client:
            return "You can't message yourself, dummy", colours['pink']

        if recipient != "invalid":
            data = "Message from " + clients[client][0] + ": " + ' '.join(args[2:])
            length = msg_len(data)
            color = colours['whisper-gray']
            type = "SysCmd"
            recipient.send((type+length+color+"1"+data+"000").encode())
            return f"Message to {clients[recipient][0]}: {' '.join(args[2:])}", color
        else:
            data = "The recipient is not connected!"
            return data, colours['pink']

    is_admin = clients[client][1]

    '''
    Logging in as admin
    We need to check if user is already an admin or not,
    and receive the password.
    '''
    if command == "login":
        if is_admin:
            data = "You're already admin!"
            color = colours['orange-warning']
            return data, color
        else:
            print(f"Logging {clients[client][0]} in")

            retrieve_key()
            print(''.join(args[1:]), KEY[0])
            passw = encode(''.join(args[1:]), KEY[0])
            clients[client] = [clients[client][0], passw == admin_password]
            success = passw == admin_password
            print('Logged in!' if success else "Login failed.")

            data = 'Logged in!' if success else "Login failed."
            color = colours['low-green'] if success else colours['red']

            return data, color

    '''
    Admin commands,
    close/end/kick/boot
    '''
    if not is_admin and command in ["end", "close", "color", "boot", "kick", "logout"]:
        data = "You don't have access to this command."
        color = colours['red']
        return data, color
    if is_admin:
        if command in ["end", "close"]:
            try:
                server_up[0] = False
                close_server()
            except OSError:
                pass

        if command == "color":
            return f"[color]{clients[client][0]}: {' '.join(args[2:])}", args[1][1:]

        if command == "logout":
            clients[client][1] = False
            return "Logged out.", colours['low-green']

        if command in ["boot", "kick"]:
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

            send_update(start_chain=True, end_chain=True)

    return "No Command Activated", "NOBGCL"


def handle_client(client):  # Takes client socket as argument.
    """Handles a single client connection."""
    try:
        name = client.recv(50).decode()
        banned_words = ["@", ":", COMMAND_PREFIX] + [x[0] for x in clients.values()]

        client.send("SysCmd".encode())  # start command chain

        banned_words_used = [key_word for key_word in banned_words if name.find(key_word) != -1]

        while len(banned_words_used) != 0 or (len(name) > 16 or len(name) < 3):
            if len(name) > 16 or len(name) < 3:
                data = "Name must be between 3-16 characters"
                # 3-Length 6-Color 1-Display || Data
                header = msg_len(data) + "DD0909" + "1"
                client.send((header + data).encode())
            else:
                data = "Invalid nickname, the name is either taken\nor it has an illegal character"
                # 3-Length 6-Color 1-Display || Data
                header = msg_len(data) + "DD0909" + "1"
                client.send((header + data).encode())
            print(f"Illegal login attempt: {name} || {banned_words_used}")
            name = client.recv(50).decode()
            banned_words_used = [key_word for key_word in banned_words if name.find(key_word) != -1]

        # client.send("000".encode())  # terminate command chain by sending command length 0.

    except ConnectionResetError:  # 10054
        print("Client error'd out.")
        del addresses[client]
    else:
        connection_working = True
        print("Handling client")
        data = 'Welcome %s! If you ever want to quit, type quit() or press [X] to exit.' % name

        header = msg_len(data) + "NOBGCL" + "1"
        # 6-Type 3-Length 6-Color 1-Display || Data
        client.send((header + data + "000").encode())

        data = "%s has joined the chat!" % name
        header = "SysCmd" + msg_len(data) + colours['low-green'] + "1"
        broadcast(header + data)
        broadcast("000")
        clients[client] = [name.replace(" ", "_"), False]

        # Chain already started in previous broadcast
        send_update(start_chain=True, end_chain=True)

        while server_up[0]:
            length, msg_type, color = 0, "", ""
            try:
                print(f'Entire buffer: {client.recv(1000, MSG_PEEK)}')
                length, msg_type, color = int(client.recv(3)), client.recv(6).decode(), client.recv(6).decode()

                data = client.recv(length).decode()
                print(F"{clients[client][0]}: {data}")
            except ConnectionResetError:  # 10054
                connection_working = False
            except ConnectionAbortedError:
                connection_working = False

            if connection_working and data != "quit()":
                if msg_type == "Normal":
                    # 6-Type 3-Length 6-Color || Data  # normal message always displayed
                    header = "Normal" + str(len(f"{clients[client][0]}: {data}".encode())).zfill(3) + color
                    broadcast(header + clients[client][0] + ": " + data)
                else:
                    data, color = handle_command(data=data, client=client)
                    header = "SysCmd" + str(len(data.encode())).zfill(3) + color + "1"
                    if msg_type == "EvrCmd":
                        broadcast(header + data + "000")

                    elif msg_type == "SlfCmd":
                        client.send((header + data + "000").encode())

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


def broadcast(msg):
    """Broadcasts a message to all the clients."""
    for sock in clients:
        try:
            sock.send(msg.encode())
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
