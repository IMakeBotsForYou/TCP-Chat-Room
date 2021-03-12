"""Server for multi-threaded (asynchronous) chat application."""

from helper_functions import *

# Encryption key
KEY = 0
port = 0
# Last time the key was updated
last_update = 0
# Is the server still running? (For shutdown command)
server_up = [True]
# Colours library
colours = {
    "red": "dd0404",
    "pink": "ff6666",
    "low-yellow": "d9c000",
    "orange-warning": "D49B00",
    "low-green": "339966",
    "bright-green": "27DB03",
    "blue": "0066cc",
    "whisper-gray": "ab9aa0",
    "white": "FFFFFF"
}

# All command usages
usage = {
    "nick": "/nick new name: Rename Yourself!",
    "nickname": "/nickname new_name: Rename Yourself!",
    "w": "/w name: whisper to someone",
    "whisper": "/whisper name: whisper to someone",
    # "online": "/online: show who's online!",   # One parameter commands never get usage'd
    # "current": "/current: show who's online!", # One parameter commands never get usage'd
    # "time": "/time: shows the server time",    # One parameter commands never get usage'd
    "login": "/login password Try logging in as admin!",
    "block": "/block username You can't see a users messages anymore.\nTo revert, do /unblock <username>",
    "purge": "/purge number: delete (positive) X amount of messages",
    "color": "admin_/color #color message: send a message with a special bg",
    "kick": "admin_/kick username: kicks a user",
    "reminder": "/reminder seconds: Remind you to talk after x seconds. (min 5)",
    "boot": "admin_/boot username: kicks a user",
    # "logout": "admin_/logout: logs out of admin mode",  # One parameter commands never get usage'd
    # "end": "admin_/end: Ends server lol",               # One parameter commands never get usage'd
    # "close": "admin_/end: Ends server lol"              # One parameter commands never get usage'd
}

command_list = ["Command List:",
                "/nick or /nickname <new name>: Rename Yourself",
                "/w or /whisper <name>: whisper to someone",
                "/online or /current: show who's online",
                "/purge <number>: delete the last X lines",
                "/time: show the server's time",
                "/update_key: Force update your key",
                "/reminder <seconds>: Remind you to talk after x seconds",
                "/login <password>: Try logging in as admin."]  # I do this so you can minimize the list
command_list = "\n".join(command_list)
# "/boot or /kick: kicks a user by username",
#
admin_cmd_list = ["/end, or /close: closes server",
                  "/kick: kicks a user by username",
                  "/color <#colour>: send message with bg colour",
                  "/logout: exit admin mode."]  # I do this so you can minimize the list
admin_cmd_list = "\n".join(admin_cmd_list)

# Password for logging in as admin
admin_password = "danIsTheKing"
# Command prefix for user
COMMAND_PREFIX = "/"
# camera sockets list
cameras = {}
clients = {}
addresses = {}


def format_message(msg_type, color, display, data):
    try:
        return msg_type + msg_len(data.encode()) + color + display + data
    except:
        return msg_type + msg_len(data) + color + display + data


def accept_incoming_connections():
    """
    First checks if a connection is a server-scanner or a client.
    If it's a user, it accepts the connection and sends them a welcome message.
    Then, we start a thread for that user and handle their input.
    """
    while server_up[0]:
        try:
            # Accept the user
            client, client_address = SERVER.accept()
            user_mode = client.recv(1).decode()
            # Are you a scanner or a client?
            # 0 -> checker
            # 1 -> user
            # 2 -> camera

            if user_mode == "0":
                print(f"We've been scanned by {client_address[0]}")
                continue

            if user_mode == "2":
                camera = Thread(target=lambda: handle_camera(client, client_address))
                camera.start()
                cameras[client] = client_address
                continue

            print(f"{client_address} has connected.")
            data = "Greetings from the cave! Now type your name and press enter!\n" \
                   "After you login, Enter /help or /commands to see the command collection_list!\n" \
                   "If someone's text is jumbled up, please ask them to use /update_key."
            # Type - Command, Length = len(data), Color - NOBGCL, Display - 1
            header = "SysCmd" + msg_len(data) + "NOBGCL" + "1"
            client.send((header + data + "000").encode())  # 000 => terminate command sequence
            addresses[client] = client_address
            Thread(target=handle_client, args=(client,)).start()
            print(f"Starting thread for {client_address}")

        except OSError:
            close_server()
            break


def why_arent_you_talking(client):
    """
    Checks the time between the user's last message and now,
    if over the specified time, send a message.
    :param client: client being checked
    :return: None
    """
    current_time = int(time.time())
    try:
        if current_time - clients[client]['last_message'] > clients[client]['reminder_interval']:
            # Is the current time more than last message + reminder interval?
            data = f"Oi mate, you haven't talked for {clients[client]['reminder_interval']} seconds; Look alive!"
            length = msg_len(data)
            # Send reminder
            client.send(f"SysCmd{length}{colours['blue']}1{data}000".encode())
            # Update last time to now
            clients[client]['last_message'] = current_time
    except KeyError:
        # If there's an error then stop looping this
        kick(client, delete=True)
        return "stop"


def get_client(val, ip=False):
    """
    :param val: name to search
    :param ip: Search by ip? (default off)
    :return Client OBJ
    Gets client by name or IP
    """
    if ip:
        # Addresses{} holds IP:PORT pairs
        for key, value in addresses.items():
            if val == F"{value[0]}:{value[1]}":
                return key, clients[key][0]
    else:
        # Clients holds names
        for key, value in clients.items():
            if val == value[0]:
                return key, clients[key]
    return "invalid", "invalid"


def kick(client, delete=True, cl=False, message=True, custom=""):
    """
    :param client: The client being kicked/removed
    :param delete: Delete the client from the client collection_list
    :param cl:  The server is being closed, so no need to say who left.
    :param message: Do we tell them they're kicked or no?
    :param custom: Custom kick message
    Kicks a user.
    """
    clients[client]['reminder_function']()  # stop calling him again.
    if message:
        if custom == "":
            data = "Kicked"
            header = "SysCmd" + msg_len(data) + colours['red'] + "0"
            client.send((header + data + "000").encode())
        else:
            data = "Kicked. Reason: " + custom
            header = "SysCmd" + msg_len(data) + colours['red'] + "0"
            client.send((header + data + "000").encode())
    if not cl:
        user = "%s has left the chat." % clients[client]['nick']
        length = msg_len(user)
        broadcast(f"SysCmd{length}NOBGCL1{user}000")

    try:
        # # # # # # # #  Type     Length    Colour        Display      Message      # # # # # # # #
        client.send(("SysCmd" + "013" + colours['white'] + "0" + "Kindly, leave" + "000").encode())

        if delete:
            print(f"Deleted {clients[client]}")
            del clients[client]
            del addresses[client]
            print(f"{len(clients.values())} Users remaining")

    except ConnectionResetError:
        pass
    except Exception as E:
        print(E)

    send_update(start_chain=True, end_chain=True)


def close_server():
    """
    Closes the server by kicking everyone, then deleting them.
    :return: None
    """
    for x in clients:
        try:
            kick(x, delete=False, cl=True)
        except OSError:
            pass
    lst = list(clients.keys()).copy()
    for x in lst:
        clients.pop(x, None)
    server_up[0] = False
    SERVER.close()


def handle_camera(client, address):
    global port
    nick = F"{address[0]}:{address[1]}"
    run = True
    display = True
    while run:
        try:
            # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
            buffer_check = client.recv(5, MSG_PEEK).decode()
            if buffer_check in ["LEAVE", "faild"]:
                nick_header = f"{msg_len(nick, 3)}{nick}"
                broadcast(f"LEAVE{nick_header}", cameras)
                run = False
                continue

            # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
            nick_header = f"{msg_len(nick, 3)}{nick}".encode()
            diamensions_header = client.recv(8).decode()
            frame_size_s = client.recv(8).decode()
            frame_size = int(frame_size_s)

            # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
            data = client.recv(frame_size)
            while len(data) < frame_size:
                data += client.recv(frame_size - len(data))

            # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
            if display:
                frame = np.frombuffer(data, dtype="uint8")
                frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                frame.resize((int(diamensions_header[:4]), int(diamensions_header[4:]), 3))
                cv2.imshow(nick, frame)
            # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

            data = nick_header + (diamensions_header + msg_len(data, 8)).encode() + data
            broadcast(data, cameras)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyWindow(nick)
                display=False
            # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        except:
            run=False
    cv2.destroyWindow(nick)
    print(f"{nick} has errored, or logged out.")


def send_update(start_chain, end_chain):
    """
    :param start_chain: Start a command chain (SysCmd)
    :param end_chain: End the command chain (000)
    :return: None
    Broadcasts to all users to update the user number, and user list
    This happens when a nickname is changed, or a user joins/leaves.
    """
    chain = "SysCmd" if start_chain else ""

    # Start, or continue existing chain with number of users
    data = f"Update user_num,{str(len(clients.values())).zfill(2)}"
    header = msg_len(data) + colours['white'] + "0"
    chain += header + data

    # No need for type because chain has already begun.
    # We do this even if the number hasn't changed
    # to handle nickname changes.
    data = f"Update members{'+'.join([x['nick'] for x in clients.values()])}"
    header = msg_len(data) + colours['white'] + "0"
    chain += header + data
    broadcast(chain)
    print(
        f"Updated users list: {str(len(clients.values())).zfill(2)}-{', '.join([x['nick'] for x in clients.values()])}",
        end=" ")
    if end_chain:
        print("with kill")
        broadcast("000")  # kill command chain


def handle_command(data, client):
    """
    :param data: The message
    :param client: The client being handled.
    If the user has sent a command, instead of a normal message -
    we need to handle it properly.
    """
    global last_update, KEY
    # split command into args
    args = data.strip().split(" ")
    args = list(filter(None, args))
    # first arg is the command name, after the '/'
    command = args[0][len(COMMAND_PREFIX):]
    ignore = "ignore", "NOBGCL"
    if command == "time":
        return f"Current server time: |{time.ctime(time.time())}|", "NOBGCL"
    if command == "boot":
        return f"This command is currently disabled.", "NOBGCL"
    if command == "purge":
        try:
            number = int(args[1])
            if number < 1:
                raise ValueError
            # Number must be positive integer
            data = "Purged " + str(number) + " messages."
            return data, "NOBGCL"
        except ValueError:
            data = "usage_purge"
        except IndexError:
            data = "usage_purge"

    if command == "reminder":
        try:
            seconds = int(args[1])
            if seconds < 5:
                raise ValueError
            clients[client]['reminder_interval'] = seconds
            # Change reminder interval for this user.
            return f"Reminder interval changed to {seconds}", colours['low-green']
        except ValueError:
            data = "usage_reminder"
        except Exception as e:
            print(e)

    if command in ["commands", "help"]:
        data = command_list
        # Display command list
        if clients[client]['admin']:
            data += "\n" + admin_cmd_list
        return data, "NOBGCL"

    if command in ["w", "whisper"]:
        recipient_name = args[1]
        recipient, _ = get_client(recipient_name)
        # recipient (sock), recipient name (we already have it)
        if recipient == client:
            # if recipient is caller
            return "You can't message yourself, dummy", colours['pink']

        # If such a user exists
        if recipient != "invalid":
            data = "Message from " + clients[client]['nick'] + ": " + ' '.join(args[2:])
            length = msg_len(data)
            print(len(data), length)
            # oooo mysterious gray whisper colour
            color = colours['whisper-gray']
            msg_type = "SysCmd"
            recipient.send((msg_type + length + color + "1" + data + "000").encode())
            return f"Message to {clients[recipient][0]}: {' '.join(args[2:])}", color
        else:
            # If that user doesn't exist, say they're not here!
            data = "The recipient is not connected!"
            return data, colours['pink']

    if command in ["current", "online"]:
        return f"{len(clients)} users online {' | '.join([x['nick'] for x in clients.values()])}", "NOBGCL"

    if command in ["nick", "nickname"]:
        if len(args) > 1:
            recipient_name = args[1]
            banned_keywords = ["{System}", "@", ":", COMMAND_PREFIX]
            # Can't have you messing up my shtuff
            if len([x for x in banned_keywords if recipient_name.find(x) != -1]) != 0:
                return "Invalid nickname".encode(), colours['red']

            recipient, _ = get_client(recipient_name)
            # Check if that's one of the already existing names
            if recipient == "invalid":
                # If not continue
                prev_name = clients[client]['nick']
                clients[client]['nick'] = "_".join(word for word in args[1:] if word != "")

                send_update(start_chain=True, end_chain=False)
                a = "'nick'"
                data = f'{prev_name} renamed to: "{clients[client][a]}"'
                length = msg_len(data)
                broadcast(f'{length}NOBGCL1{data}000')
                return "Nickname Updated.", colours['low-green']
            else:
                return f'That name is taken.', colours['orange-warning']
        else:
            return "Must enter a nickname.", colours['red']

    # Now admin commands →　
    is_admin = clients[client]['admin']

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
            print(f"Logging {clients[client]['nick']} in")

            last_update, KEY = retrieve_key(last_update, KEY)
            passw = encode(''.join(args[1:]), KEY)
            admin_pass = req.get("https://get-api-key-2021.herokuapp.com/").json()['pass']
            clients[client]['admin'] = passw == admin_pass
            success = passw == admin_pass
            # Decode what the user has sent.
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
        client.send(f"SysCmd{msg_len(data)}{color}1{data}000".encode())
        return ignore
    if is_admin:
        if command in ["end", "close"]:
            try:
                server_up[0] = False
                close_server()
            except OSError:
                pass

        if command == "color":
            return f"[color]{clients[client]['nick']}: {' '.join(args[2:])}", args[1][1:]

        if command == "logout":
            clients[client]['admin'] = False
            return "Logged out.", colours['low-green']

        if command in ["kick"]:
            recipient_name = args[1]
            # Are we kicking an ip or a name?
            if search(r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)",
                      recipient_name):
                recipient, recipient_name = get_client(recipient_name, True)
            else:
                recipient, _ = get_client(recipient_name)
            if recipient != "invalid":
                if len(args) > 2:
                    kick_msg = ' '.join(args[2:])
                else:
                    kick_msg = ""
                print(f"\n{recipient_name} kicked for {kick_msg}\n")
                kick(recipient, delete=True, message=True, custom=kick_msg, cl=True)
                # it's gonna say that he left anyway so cl is true here
                send_update(start_chain=True, end_chain=True)
                try:
                    return f"{recipient_name} was kicked by {clients[client]['nick']}", "NOBGCL"
                except:
                    return F"{recipient_name} kicked himself??", "NOBGCL"
            else:
                data_1 = "User isn't connected"
                length = msg_len(data_1)
                client.send(("SysCmd" + length + "NOBGCL" + "1" + data_1 + "000").encode())
                return ignore

    # In case something is invalid, we put this at the end.
    # split command into args
    args = data.strip().split(" ")
    args = list(filter(None, args))
    if data.find("usage_") != -1:
        msg_type = "SysCmd"
        command = args[0][len("usage_"):]
        admin_command = usage[command][:6] == "admin_"
        if (not is_admin and admin_command) or (command not in usage):
            message = format_message(msg_type, colours['red'], "1", "Usage: Not a valid command")
            client.send((message + "000").encode())
            return ignore

        if admin_command:
            data = f"Usage: {usage[command][6:]}"
            message = format_message(msg_type, colours['red'], "1", data)
            client.send((message + "000").encode())
            return ignore

        data = f"Usage: {usage[command]}"
        message = format_message(msg_type, colours['red'], "1", data)
        client.send((message + "000").encode())
        return ignore

    return "No Command Activated", "NOBGCL"


def handle_client(client):  # Takes client sock as argument.
    """
    Handles a single client connection.
    This is done by first registering a valid name.
    Then we handle every message, from normal, Commands everyone can see,
    and commands only the user can see.
    """
    try:
        name = client.recv(1024).decode()
        banned_words = ["@", ":", COMMAND_PREFIX]
        names = [x['nick'] for x in clients.values()]

        client.send("SysCmd".encode())  # start command chain

        banned_words_used = [key_word for key_word in banned_words if name.find(key_word) != -1]
        banned_words_used += [x for x in names if name == x]
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
            if name:
                print(f"Illegal login attempt: {name} || {banned_words_used}")
            name = client.recv(50).decode()
            banned_words_used = [key_word for key_word in banned_words if name.find(key_word) != -1]
            banned_words_used += [x for x in names if name == x]
        print(f"{client}\n has registered as {name}")

    except ConnectionResetError:  # 10054
        print("Client error'd out.")
        del addresses[client]
    except ConnectionAbortedError:
        # user checking ports
        del addresses[client]
        pass
    except UnicodeDecodeError:
        data = "Something went wrong."
        client.send(("SysCmd" + msg_len(data) + colours['red'] + '1' + data + '000').encode())
        del addresses[client]
        pass
    else:
        connection_working = True
        # get a port that's free for both the server
        # and the client, to communicate on the camera port.
        data = 'Welcome %s! If you ever want to quit, type quit() or press [X] to exit.' % name
        header = msg_len(data) + "NOBGCL" + "1"
        # 6-Type 3-Length 6-Color 1-Display || Data
        client.send((header + data + "000").encode())

        data = "%s has joined the chat!" % name
        header = "SysCmd" + msg_len(data) + colours['low-green'] + "1"
        broadcast(header + data)
        broadcast("000")

        # Name, Admin, Last Message Time, Reminder Time
        clients[client] = {
            "nick": name.replace(" ", "_"),
            "admin": False,
            "last_message": int(time.time()),
            "reminder_interval": 15,
            "reminder_function": call_repeatedly(5, why_arent_you_talking, client),
            "camera_sock": socket(AF_INET, SOCK_STREAM)
        }
        data = "connect_camera"
        client.send(f"SysCmd{msg_len(data)}NOBGCL0{data}000".encode())
        # Chain already started in previous broadcast
        send_update(start_chain=True, end_chain=True)
        # try:
        while server_up[0]:
            length, msg_type, color = 0, "", ""
            try:
                x = client.recv(5000, MSG_PEEK).decode()
                if x == "006NormalNOBGCLquit()":
                    try:
                        kick(client, message=False, delete=True, cl=False)
                    except ConnectionResetError:  # 10054
                        print("Client did an oopsie")
                        del clients[client]
                    except ConnectionAbortedError:
                        print("Client did an oopsie")
                        del clients[client]
                    except OSError:
                        print("Client did an oopsie")
                        del clients[client]
                    except KeyError:
                        print(f"Client is already gone.")
                    break

                msg_type, length, color = client.recv(6).decode(), int(client.recv(3).decode()), client.recv(6).decode()
                data = client.recv(length).decode()
                clients[client]['last_message'] = int(time.time())
                print(
                    F"{'<ADMIN> ' if clients[client]['admin'] else ''}{clients[client]['nick']}: {data}" + '{0:>50}'.format(
                        F"({data.strip().split(' ')})"))
            except ConnectionResetError:  # 10054
                connection_working = False
            except ConnectionAbortedError:
                connection_working = False

            if connection_working and data != "quit()":
                if msg_type == "Normal":
                    # 6-Type 3-Length 6-Color || Data  # normal message always displayed
                    m = F"{'<ADMIN> ' if clients[client]['admin'] else ''}{clients[client]['nick']}: {data}"
                    header = "Normal" + msg_len(m) + color
                    broadcast(header + m)
                else:
                    data, color = handle_command(data=data, client=client)
                    header = "SysCmd" + msg_len(data) + color + "1"
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
                except ConnectionAbortedError:
                    print("Client did an oopsie")
                    del clients[client]
                except OSError:
                    print("Client did an oopsie")
                    del clients[client]
                except KeyError:
                    print(f"Client is already gone.")
                break
        # except Exception as e:
        #     print(f"An error has occured.\n{e}")


def broadcast(msg, list=None):
    """Broadcasts a message to all the clients."""
    if list is None:
        list = clients
    for sock in list:
        try:
            sock.send(msg.encode())
        except AttributeError:
            sock.send(msg)
        except ConnectionResetError:  # 10054
            try:
                print(f"Error in sending {msg} to {sock}")
                pass
            except ConnectionResetError:
                continue
            except ConnectionAbortedError:
                continue


HOST = ""
PORT = 45_000

mode = input("WAN server or LAN server?  (wan/lan) > ").lower()
while mode not in ["wan", "lan"]:
    print("Invalid.")
    mode = input("WAN server or LAN server?  (wan/lan) > ").lower()

"""
If mode is lan, then choose a random port and host on NAT
If mode is wan, assume user has set up port forwarding,
and request a port to host the server on.
"""
ip, port = 0, 0
stop_calling = None
if mode == "lan":
    # LAN server, pick a random port.
    PORT = 0
    SERVER = socket(AF_INET, SOCK_STREAM)
    SERVER.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    ADDR = (HOST, PORT)
    SERVER.bind(ADDR)
    ip = gethostbyname(gethostname())
    port = SERVER.getsockname()[1]
    # Add the server to active connections
    post_request(f"/servers/add/{ip}/{port}/local")
    # calls after 10 second delay, then every 10 seconds
    stop_calling = call_repeatedly(45, post_request, f"/servers/add/{ip}/{port}/local")

else:
    SERVER = socket(AF_INET, SOCK_STREAM)
    SERVER.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    port = input("Enter PortForwarding PORT > ")
    while not port.isnumeric():
        port = input("Enter PortForwarding PORT > ")
    port = int(port)
    ADDR = (HOST, port)
    print(ADDR)
    ip = req.get('https://api.ipify.org').text
    SERVER.bind(ADDR)
    post_request(f"/servers/add/{ip}/{port}/wan")
    # Add the server to active connections
    # calls after 10 second delay, then every 10 seconds
    stop_calling = call_repeatedly(45, post_request, f"/servers/add/{ip}/{port}/wan")

SERVER.listen(5)
print(f"---------------------------------------------------------")
print(f"Starting {mode} server, on {ip}:{port}, @ {time.ctime(time.time())}")
print("Waiting for connection...")
accept_incoming_connections()

SERVER.close()
stop_calling()
print(f"END LOG")
print(f"---------------------------------------------------------")
