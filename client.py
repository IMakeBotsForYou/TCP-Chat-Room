"""Script for Tkinter GUI chat client."""
from PIL import ImageTk, Image
from pyperclip import copy
from helper_functions import *

# ----Functionality---- #
current_window = 0
mode = "none"
typing_my_name = [True]  # fix global
command_prefix = "/"
name = ""

# ----TK_inters obj---- #
last_item = [0]  # fix global
online_num = [0]  # For the messages to be sent.
online_member_number_but_its_an_int = [1]

# ---- encryption ---- #

enc_vars = {
    "key": 0,
    "last_update": 0
}

# ----sockets part---- #
load_servers = None
HOST = "0"
PORT = 0
BUFFER_SIZE = 1024
client_socket = socket(AF_INET, SOCK_STREAM)  # fix global


class EntryWithPlaceholder(tk.Entry):
    """
    Create an Entry widget with a placeholder text
    that disappears when focused in, and reappears when
    focused out
    """

    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey'):
        super().__init__(master)

        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']
        self['justify'] = "center"
        self.bind("<FocusIn>", self.foc_in)
        self.bind("<FocusOut>", self.foc_out)

        self.put_placeholder()

    def put_placeholder(self):
        self.insert(0, self.placeholder)
        self['fg'] = self.placeholder_color

    def foc_in(self, *args):
        if self['fg'] == self.placeholder_color:
            self.delete('0', 'end')
            self['fg'] = self.default_fg_color

    def foc_out(self, *args):
        if not self.get():
            self.put_placeholder()


def find_end(message, item):
    """
    :param message: The message we're searching in
    :param item: What we're searching
    :return: The index where the item ends in the string
    """
    return message.find(item) + len(item)


def on_closing(tk_obj, messenger=None, event=None):
    """
    :param tk_obj: TKobject to close
    :param messenger: Entry object in chatter window
    :param event: close event
    This function is to be called when the window is closed.
    This function throws you back to whatever previous window you were in
    and closes the window entirely if the current window is mode select
    """
    global current_window, mode
    # 0 = mode select
    # 1 = Server List mode select
    # 2 = CUSTOM mode select
    # 3 = chatter window
    if current_window == 0:
        tk_obj.destroy()

    if current_window in [1, 2]:
        mode_select(tk_obj)

    if current_window == 3:
        if typing_my_name[0]:
            # Still writing name, so we can't send quit message.
            if mode == "custom":
                custom_server_select(tk_obj)
                current_window = 2
            else:
                server_list(tk_obj)
                current_window = 1
        else:
            # Already wrote my name
            messenger.set("quit()")
            send(messenger, tk_obj)


def encrypt_few_words(msg, start=0, end=-1):
    """
    :param msg: Message to handle
    :param start: start index (in argument list)
    :param end: end position (in argument list) + 1
    :return: encrypted string
    """
    args = msg.split(" ")
    end = end if end != -1 else len(args) - 1
    for i in range(start, end + 1):
        args[i] = encode(args[i], enc_vars['key'])
    return ' '.join(args)


def format_message(args):
    """
    :param args: message args (split(" "))
    :return: formatted length, type, color, and message ready to send.
    """
    global name
    enc_vars['last_update'], enc_vars['key'] = retrieve_key(enc_vars['last_update'], enc_vars['key'])
    msg = ' '.join(list(filter(None, args)))  # remove extra spaces
    args = list(filter(None, args))  # remove extra spaces

    color = "NOBGCL"
    msg_type = "Normal"
    if msg == f"{command_prefix}update_key":
        enc_vars['last_update'], enc_vars['key'] = retrieve_key(enc_vars['last_update'], enc_vars['key'], force=True)
        msg = ""

    if msg == "quit()":
        return msg_len(msg.encode()), msg_type, color, msg

    everyone_commands = ["kick", "color", "boot"]
    you_commands = ["w", "whisper", "current", "online",
                    "login", "logout", "block", "nick",
                    "nickname", "help", "commands", "purge",
                    "reminder", "time", "end", "close"]

    command = args[0][len(command_prefix):]
    if typing_my_name[0]:
        msg = "_".join(args)
        length = msg_len(msg)
        color = "04CC04"
        return length, msg_type, color, "_".join(args)
    if command in everyone_commands:
        msg_type = "EvrCmd"
        color = "904010"

        if command in ["nick", "nickname"]:
            if len(args) < 3:
                msg = f"usage_{command}"
            else:
                name = '_'.join(args[1:])
                msg = f'{args[0]} {name}'

        if command == "color":
            if len(args) < 3:
                msg = f"usage_{command}"
            else:
                if search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', args[1]):
                    color = args[1][1:]
                    msg = encrypt_few_words(' '.join(args), 2)
                else:
                    msg = "usage_color"  # invalid, will not send

        if command in ["kick", "boot"]:
            if len(args) < 2:
                msg = f"usage_{command}"
            else:
                color = "AA0000"
                msg = encrypt_few_words(msg, 2)

    elif command in you_commands:
        msg_type = "SlfCmd"

        if command in ["w", "whisper"]:

            if len(args) < 3:
                msg = f"usage_{command}"
            else:
                color = "ab9aa0"
                msg = encrypt_few_words(msg, 2)

        if command == "login":
            if len(args) < 2:
                msg = f"usage_{command}"
            else:
                msg = encrypt_few_words(msg, 1)
        if command == "purge" and len(args) < 2:
            msg = "usage_purge"
    else:
        # Normal message
        msg = encrypt_few_words(msg)

    length = msg_len(msg.encode())
    return msg_type, length, color, msg


def handle_incoming_command(data, tk_obj):
    """
    :param data: The command we're dealing with
    :param tk_obj: Root window
    :return: Handles, and returns the fitting data to display from a command.
    """
    global mode
    print(data)
    if data[:7] == "[color]":
        return encrypt_few_words(data[7:], 1)

    elif data.find("Purge") != -1:
        number = int(data.split(' ')[1])
        msg_list = tk_obj.winfo_children()[0].winfo_children()[1]
        purge(number, msg_list)

    elif data[:6] == "Kicked":
        reason = find_end(data, ". ") != 1
        if reason:
            mb.showinfo("Info", f"You've been kicked.\n"
                                f"Reason: {encrypt_few_words(data[find_end(data, 'Kicked. Reason: '):])}")
        else:
            mb.showinfo("Info", "Oh no! You've been kicked.")

        if mode == "custom":
            custom_server_select(tk_obj)
        else:
            server_list(tk_obj)
        return

    elif data.find("was kicked by") != -1:
        # Name was kicked by Name for Reason
        reason = find_end(data, "for") != -1
        if reason:
            return encrypt_few_words(data, 6)

    elif data.find("Welcome") != -1:
        typing_my_name[0] = False

    elif data.find("Update user_num") != -1:
        online_member_number_but_its_an_int[0] = int(data[data.find(",") + 1:])
        online_num[0].set(f'Users online: {online_member_number_but_its_an_int}')

    elif data.find("Update members") != -1:
        members = data[14:].split("+")
        names = tk_obj.winfo_children()[1].winfo_children()[1]
        names.delete(0, tk.END)  # delete all users
        for member in members:
            # add them back with new user / nickname
            names.insert(tk.END, member)

    elif data.find("Message from") != -1 or data.find("Message to") != -1:
        data = encrypt_few_words(data, 3)
        print(f'Decrypting... ->  {data}')

    # current users online
    elif data.find("users online") != -1:
        before = data[:find_end(data, "users online")] + ":\n"
        after = " | ".join([x for x in data[len(before) - 1:].split(" | ")])
        data = before + after

    elif data[:find_end(data, "[color]")] == "[color]":
        data = encrypt_few_words(data[7:], 1)

    elif data == "Kindly, leave":
        if mode == "custom":
            custom_server_select(tk_obj)
        else:
            server_list(tk_obj)
        return

    return data


def black_or_white(color):
    """
    :param color: Background colour.
    :return: White or black foreground, depending on which is easier to see
    Based on the formula
    if red * 0.299 + green * 0.587 + blue * 0.114 > 186 black else white
    """
    color = "2c2f33" if color == "NOBGCL" else color
    red = int(f"0x{color[:2]}", 16)
    green = int(f"0x{color[2:4]}", 16)
    blue = int(f"0x{color[4:6]}", 16)
    return "#000000" if red * 0.299 + green * 0.587 + blue * 0.114 > 186 else "#ffffff"


def purge(amount, listbox):
    """
    :param amount: Amount of messages to delete
    :param listbox: messages listbox
    Doesn't allow to delete first 3 messages.
    """
    start = listbox.size() - amount
    if start < 4:
        start = 4
        listbox.delete(start, listbox.size() - 1)
        listbox.insert(tk.END, "Can't delete first 4 messages")
        last_item[0] = listbox.size()-1
    else:
        listbox.delete(start, listbox.size() - 1)
        last_item[0] = last_item[0] - amount


def receive(tk_obj, client_sock):
    """
    :param tk_obj: TK_obj for scope purposes.
    :param client_sock: Receives from the client sock
    Friendly output, and handling of messages from the server.
    """
    while True:
        try:
            msg_list = tk_obj.winfo_children()[0].winfo_children()[1]
            msg_list.see("end")
            data = "NO DATA"
            color = "#BBBBBB"

            # accessing all the damn frames and that
            # 6-Type 3-Length 6-Color 1-Display || Data
            msg_type = client_sock.recv(6).decode()
            print("New Message:")
            print("Type: " + msg_type, end=" | Entire message: ")
            print(client_sock.recv(1000, MSG_PEEK).decode())
            enc_vars['last_update'], enc_vars['key'] = retrieve_key(enc_vars['last_update'], enc_vars['key'])
            if msg_type == "SysCmd":
                next_command_size = client_socket.recv(3).decode()
                print("Size: " + next_command_size, end=" | ")

                color = client_sock.recv(6).decode()
                color = "2c2f33" if color == "NOBGCL" else color
                print("Color: " + color, end=" | ")
                # Runs until it hits a command with length 0,
                # Signaling the end of the communication.
                print("Data:", end=" ")
                while next_command_size != "000":
                    display = client_socket.recv(1).decode()
                    data = client_socket.recv(int(next_command_size)).decode()
                    print(data)
                    # 1 display | 0 don't display
                    if display == '1':
                        msg = handle_incoming_command(data=data, tk_obj=tk_obj)
                        if msg != "ignore":
                            for line in msg.split("\n"):
                                try:
                                    msg_list.insert(tk.END, line)
                                    last_item[0] += 1
                                    msg_list.itemconfig(last_item[0], bg=f'#{color}', fg=black_or_white(color))
                                except tk.TclError:  # server closed
                                    pass
                                if line.find(f'@{name}') != -1:
                                    msg_list.itemconfig(last_item[0], bg='#C28241')

                    else:
                        _ = handle_incoming_command(data=data, tk_obj=tk_obj)

                    next_command_size = client_socket.recv(3).decode()
                    if next_command_size != "000":
                        color = client_sock.recv(6).decode()
                        print(f"Type: SysCmd | Size: {next_command_size} | Color: {color} | Data: | {data} |")
                # Example message:
                # SysCmd018FFFFFF0Update user_num,01017FFFFFF0Update membersDan000
                print('--------------------')
            elif msg_type == "Normal":
                size = client_socket.recv(3).decode()
                color = client_socket.recv(6).decode()
                msg = client_sock.recv(int(size)).decode()
                current_user = msg[:msg.find(": ")]
                msg = f"{current_user}: {encrypt_few_words(msg[msg.find(': ') + 2:])}"
                for line in msg.split("\n"):
                    try:
                        msg_list.insert(tk.END, line)
                        last_item[0] += 1
                        msg_list.itemconfig(last_item[0], bg=f'#{color}')
                    except tk.TclError:  # server closed
                        pass
                    if line.find(f'@{name}') != -1:
                        msg_list.itemconfig(last_item[0], bg='#C28241')
            else:
                test = msg_type + color + data + client_socket.recv(1024).decode()
                if test:
                    print("Error. Dumping data", test)

        except OSError:
            break  # Client has left the chat
        except IndexError:
            break  # Client has left the chat
        except RuntimeError:
            break  # Client has left the chat

        except Exception as e:  # if we get any other error it's bc you messed up not me
            print("You dun messed up.", e)
            print("\nBut don't worry, we handled it.")
            test = client_socket.recv(100000).decode()
            if test:
                print("Dumping data", test)
            break


def listbox_copy(event):
    """
    Copy selected message's text to clipboard
    """
    selection = event.widget.curselection()
    if selection:
        index = selection[0]
        copy(event.widget.get(index))


def go_to_dm(event, entry_field):
    """
    :param event: double click
    :param entry_field: Entry field of root menu (chatter menu)
    Automatically places /whisper <name> in your message entry field.
    """
    try:
        selection = event.widget.curselection()[0]
        if search(f"^{command_prefix}(whisper)|(w)", entry_field.get()):
            entry_field.delete('0', 'end')
        entry_field.insert(0, f'{command_prefix}whisper {event.widget.get(selection)} ')
    except IndexError:
        pass


def send(input_msg, tk_obj, event=None):
    """
    :param tk_obj: root tk()
    :param input_msg: The entry field, from which we get the message
    :param event: send event (enter, send button)
    """
    global current_window
    get = input_msg.get()
    if get == "":
        return
    enc_vars['last_update'], enc_vars['key'] = retrieve_key(enc_vars['last_update'], enc_vars['key'])
    msg_type, length, color, data = format_message(get.split(" "))
    msg = data
    if not typing_my_name[0]:
        msg = f"{msg_type}{length}{color}{data}"
        print(F"\nSent: {msg}\n")
    input_msg.set("")
    if length != "000":
        try:
            client_socket.send(msg.encode())
        except ConnectionResetError:
            mb.showinfo("Info", "Server shut down. Returning to server select.")
            if mode == "custom":
                custom_server_select(tk_obj)
                current_window = 2
            else:
                server_list(tk_obj)
                current_window = 1


def check_option(item, working_connections):
    """
    :param item: current server being checked
    :param working_connections: list of working servers so far
    """
    check = socket(AF_INET, SOCK_STREAM)
    ip = item[0]
    port = int(item[1])
    try:
        check.connect((ip, port))
        check.send("0".encode())
    except:
        print(f'{ip}:{port} Timed out - Flagging as inactive.\n')
        post_request(f'/servers/remove/{item[0]}/{item[1]}/NONE')
    else:
        working_connections.append(f"{item[0]}:{item[1]}")
    finally:
        check.close()
    return len(working_connections)


def resize_font(message_list, event=None):
    """
    :param message_list: message listbox
    :param event: resize event
    Makes the text resize dynamically to the width of the window.
    """
    if event.width < 750:
        return
    size = round(event.width / 100) + 4
    size = 11 if size < 11 else size
    try:
        message_list['font'] = ("Varela Round", size)
        message_list.see("end")
    except tk.TclError:
        pass


def confirm_config(tk_obj, ip, port):
    """
    :param tk_obj: window to remake
    :param ip: ip to connect to
    :param port: port to connect to
    Remakes the window into the chatroom window if
    we can connect, if not do nothing.
    """
    global client_socket
    enc_vars['last_update'], enc_vars['key'] = retrieve_key(enc_vars['last_update'], enc_vars['key'])
    if ip in ["Enter IP", ""]:
        print("Must enter IP")
        return
    if port in ["Enter PORT", ""]:
        print("Must enter PORT")
        return
    try:
        port = int(port)
    except ValueError:
        print("Port must be int")
        return
    addr = ip, int(port)
    print(f'Connecting to {addr}...')
    client_socket = socket(AF_INET, SOCK_STREAM)
    try:
        client_socket.connect(addr)
        client_socket.send("1".encode())
        chat_room(tk_obj)
        receive_thread = Thread(target=lambda: receive(tk_obj, client_socket))
        receive_thread.start()

    except Exception as e:
        print(f'Try a different server.\n{e}')


def verify_connections(server_list):
    """
    :param server_list: listbox
    Loops over ip, port bundles from the heroku API and
    tries connecting to each.
    """
    ip = gethostbyname(gethostname())
    connections = post_request(f'/forme/{ip}')['connections_for_me']
    working_connections = []
    threads = []
    for item in connections:
        check_thread = Thread(target=lambda: check_option(item, working_connections))
        threads.append(check_thread)
        check_thread.start()

    # Don't print anything if we didn't timeout any threads
    prt_str = f'On {join_all(threads, 1)} servers'
    if prt_str != "On None servers":
        print(prt_str)
    try:
        if len(working_connections) == 0:
            server_list.delete(0, tk.END)
            server_list.insert(tk.END, "No available servers.")
            server_list.config(state=tk.DISABLED)
        else:
            server_list.config(state=tk.NORMAL)

        # Map existing ones, and delete the inactive
        currently_listed = server_list.get(0, tk.END)

        # Loop over all WORKING connections, and add the non-listed ones
        for i, connection in enumerate(working_connections):
            if connection not in currently_listed:
                ip, port = connection.split(":")
                server_list.insert(tk.END, f"{ip}:{port}")

        # Loop over LISTED connections and delete not working ones.
        for i, listed in enumerate(currently_listed):
            if listed not in working_connections:
                server_list.delete(i)
    except Exception as e:
        print(f"Error {e} has occurred when trying to refresh server list.")


def get_selection_confirm(tk_obj, list):
    """
    :param tk_obj: TKOBJ to remake
    :param list: listbox to get selection from
    Remakes the window into the chatroom window if
    we can connect, if not, refresh the active
    server list.
    """
    global load_servers

    selection = list.curselection()
    if selection:
        index = selection[0]
        text = list.get(index)
        ip = text[:text.find(":")]
        port = int(text[text.find(":") + 1:])

        # noinspection PyTypeChecker
        works = check_option([ip, port], []) == 1
        if works:
            load_servers()
            confirm_config(tk_obj, ip, port)
        else:
            verify_connections(list)


def chat_room(tk_obj):
    """
    :param tk_obj: tkinter root
    Destroys the tkinter object and remakes
    it as a chatroom.
    """
    global online_num, current_window
    current_window = 3
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    for child in tk_obj.winfo_children():
        child.destroy()
    tk_obj.title("Chatter")
    tk_obj.resizable(width=True, height=True)
    tk_obj.minsize(700, 150)
    tk_obj.attributes("-topmost", True)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    my_msg = tk.StringVar()  # For the messages to be sent.
    my_msg.set("")
    messages_frame = tk.Frame(tk_obj)
    messages_frame.grid(row=0, column=1, columnspan=2, padx=5, pady=10, sticky="ewns")
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    scrollbar = tk.Scrollbar(messages_frame)
    scrollbar.grid(row=0, column=2, sticky="wens")
    msg_list = tk.Listbox(messages_frame, height=15, width=75, background="#2c2f33",
                          foreground="white", yscrollcommand=scrollbar.set)
    msg_list.insert(tk.END, "Loading you in. This may take a bit.")
    msg_list.bind('<<ListboxSelect>>', lambda event: listbox_copy(event))
    scrollbar.config(command=msg_list.yview)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    # Following will contain the messages.
    entry_field = tk.Entry(messages_frame, textvariable=my_msg)
    entry_field.bind("<Return>", lambda x: send(my_msg, tk_obj))
    entry_field.bind('<Control-a>', lambda event: event.widget.select_range(0, 'end'))

    entry_field.grid(row=1, column=1, sticky="wnse")
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    send_button = tk.Button(messages_frame, text="Send",
                            command=lambda: send(my_msg, tk_obj), height=2, width=10)
    send_button.grid(row=1, column=1, sticky="ens")
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    messages_frame.rowconfigure(0, weight=1)
    messages_frame.columnconfigure(1, weight=1)
    msg_list.grid(row=0, column=1, sticky="ewns")
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    # noinspection PyTypeChecker
    online_num[0] = tk.StringVar()
    online_num[0].set("Users online: [Loading...]")
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    online_users = tk.Frame(tk_obj)
    online_users.grid(row=0, column=0, padx=5, pady=10, sticky="ewns")
    scrollbar1 = tk.Scrollbar(online_users)  # To navigate through past messages.
    users_list = tk.Listbox(online_users, height=100, width=17, yscrollcommand=scrollbar1.set, background="#2c2f33",
                            foreground="white")

    online_text = tk.Label(online_users, text="Users Online", textvariable=online_num)
    # online_text.pack(side="top", fill="both")
    # users_list.pack(side="left", fill="both")
    users_list.grid(row=1, column=0, sticky="ewns")
    users_list.bind('<<ListboxSelect>>', lambda event: go_to_dm(event, entry_field))
    online_text.grid(row=0, column=0, sticky="nwse")
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    tk_obj.columnconfigure(1, weight=1)
    tk_obj.rowconfigure(0, weight=1)

    tk_obj.protocol("WM_DELETE_WINDOW", lambda: on_closing(tk_obj, my_msg))
    tk_obj.bind("<Configure>", lambda event: resize_font(msg_list, event))
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------


def custom_server_select(tk_obj):
    """
    :param tk_obj: tkinter root
    Destroys the tkinter object and remakes
    it as the custom server entry window.
    """
    global current_window
    current_window = 2

    typing_my_name[0] = True
    last_item[0] = 0
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    for child in tk_obj.winfo_children():
        child.destroy()
    tk_obj.iconbitmap('./images/list.ico')
    tk_obj.title("Choose Server CUSTOM")
    tk_obj.protocol("WM_DELETE_WINDOW", lambda: on_closing(tk_obj))
    # setting window size
    width = 800
    height = 450
    screenwidth = tk_obj.winfo_screenwidth()
    screenheight = tk_obj.winfo_screenheight()
    alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
    tk_obj.geometry(alignstr)
    tk_obj.resizable(width=False, height=False)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    image1 = Image.open("./images/bg_1.png")
    x = image1.resize((800, 450), Image.ANTIALIAS)
    test = ImageTk.PhotoImage(x)
    background = tk.Label(tk_obj, image=test)
    background.image = test
    background["justify"] = "center"
    background.place(x=0, y=0, width=800, height=450)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    ip_field = EntryWithPlaceholder(tk_obj, "Enter IP")
    ip_field.place(x=275, y=200, width=250, height=45)
    ip_field["font"] = ("Helvetica", 24)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    port_field = EntryWithPlaceholder(tk_obj, "Enter PORT")
    port_field.place(x=275, y=275, width=250, height=45)
    port_field["font"] = ("Helvetica", 24)
    confirm = tk.Button(tk_obj, text="Confirm",
                        command=lambda: confirm_config(tk_obj, ip_field.get(), port_field.get()),
                        font="summer", bd=5)
    confirm.place(x=275, y=345, width=250, height=45)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------


def server_list(tk_obj):
    """
    :param tk_obj: tkinter root
    Destroys the tkinter object and remakes
    it as the server list window.
    """
    global current_window
    current_window = 2

    typing_my_name[0] = True
    last_item[0] = 0
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    for child in tk_obj.winfo_children():
        child.destroy()
    tk_obj.iconbitmap('./images/list.ico')
    tk_obj.title("Choose Server")
    tk_obj.protocol("WM_DELETE_WINDOW", lambda: on_closing(tk_obj))
    # setting window size
    width = 800
    height = 450
    screenwidth = tk_obj.winfo_screenwidth()
    screenheight = tk_obj.winfo_screenheight()
    alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
    tk_obj.geometry(alignstr)
    tk_obj.resizable(width=False, height=False)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    image1 = Image.open('./images/server_select_bg.png')
    x = image1.resize((800, 450), Image.ANTIALIAS)
    test = ImageTk.PhotoImage(x)
    background = tk.Label(tk_obj, image=test)
    background.image = test
    background["justify"] = "center"
    background.place(x=0, y=0, width=800, height=450)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    servers = tk.Listbox(tk_obj, height=15, width=75, background="#2c2f33",
                         foreground="white")
    servers['font'] = ("Varela Round", 24)
    servers.place(x=180, y=115, width=440, height=210)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    refresh = tk.Button(tk_obj, text="Confirm Selection",
                        command=lambda: get_selection_confirm(tk_obj, servers), height=2, width=10)
    refresh.place(x=425, y=350, width=325, height=80)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    refresh = tk.Button(tk_obj, text="Refresh Servers",
                        command=lambda: verify_connections(servers), height=2, width=10)
    refresh.place(x=50, y=350, width=325, height=80)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    verify_connections(servers)

    global load_servers
    load_servers = call_repeatedly(10, verify_connections, servers)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------


def mode_select(tk_obj):
    """
    :param tk_obj: window to remake
    Wanna enter a server on your own
    or get a list of active servers?
    """
    global current_window, load_servers
    try:
        load_servers()  # call to stop loop
    except:
        pass  # if error then we haven't began the loop yet
    current_window = 0
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    typing_my_name[0] = True
    last_item[0] = 0
    for child in tk_obj.winfo_children():
        child.destroy()
    tk_obj.iconbitmap('./images/list.ico')
    tk_obj.title("Choose Server LAN")
    tk_obj.protocol("WM_DELETE_WINDOW", lambda: on_closing(tk_obj))
    # setting window size
    width = 800
    height = 450
    screenwidth = tk_obj.winfo_screenwidth()
    screenheight = tk_obj.winfo_screenheight()
    alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
    tk_obj.geometry(alignstr)
    tk_obj.resizable(width=False, height=False)

    image1 = Image.open("./images/bg_1.png")
    x = image1.resize((800, 450), Image.ANTIALIAS)
    test = ImageTk.PhotoImage(x)
    background = tk.Label(tk_obj, image=test)
    background.image = test
    background["justify"] = "center"
    background.place(x=0, y=0, width=800, height=450)
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    wan_button = tk.Button(tk_obj, text="Custom Entry",
                           command=lambda: custom_server_select(tk_obj), height=2, width=10)

    wan_button['font'] = ("Varela Round", 30)

    wan_button.place(x=80, y=170, width=290, height=150)

    lan_button = tk.Button(tk_obj, text="Server List",
                           command=lambda: server_list(tk_obj), height=2, width=10)
    lan_button['font'] = ("Varela Round", 30)
    lan_button.place(x=410, y=170, width=290, height=150)


if __name__ == "__main__":
    app = tk.Tk()
    mode_select(app)
    app.mainloop()
