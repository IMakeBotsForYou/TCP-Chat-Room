"""Script for Tkinter GUI chat client."""
from socket import AF_INET, socket, SOCK_STREAM, MSG_PEEK
from threading import Thread
from re import search
import tkinter as tk
from tkinter import messagebox as mb
from PIL import ImageTk, Image
import requests as req
import time
from pyperclip import copy

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
KEY = 0
last_update = 0  # last key update

# ----sockets part---- #
HOST = "0"
PORT = 0
BUFFER_SIZE = 1024
client_socket = socket(AF_INET, SOCK_STREAM)  # fix global


class EntryWithPlaceholder(tk.Entry):
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

    def foc_in(self):
        if self['fg'] == self.placeholder_color:
            self.delete('0', 'end')
            self['fg'] = self.default_fg_color

    def foc_out(self):
        if not self.get():
            self.put_placeholder()


def msg_len(data):
    return str(len(data)).zfill(3)


def encode(txt, key):
    return ''.join([chr(ord(a) ^ key) for a in txt])


def find_end(message, item):
    return message.find(item) + len(item)


def find_index(lst, item):
    for i in range(lst.size()):
        if lst.get(i) == item:
            return i
    else:
        return -1


def on_closing(tk_obj, messenger=None, event=None):
    """This function is to be called when the window is closed."""
    global current_window, mode
    # 0 = mode select
    # 1 = LAN mode select
    # 2 = WAN mode select
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
            send(messenger)


def encrypt_few_words(msg, start=0, end=-1):
    global KEY
    args = msg.split(" ")
    end = end if end != -1 else len(args) - 1
    for i in range(start, end + 1):
        args[i] = encode(args[i], KEY)
    return ' '.join(args)


def format_message(args):
    global name
    msg = ' '.join(list(filter(None, args)))  # remove extra spaces
    args = list(filter(None, args))  # remove extra spaces

    color = "NOBGCL"
    msg_type = "Normal"
    if msg == f"{command_prefix}update_key":
        update_key(True)
        msg = ""

    if msg == "quit()":
        return msg_len(msg.encode()), msg_type, color, msg

    everyone_commands = ["kick", "color"]
    you_commands = ["w", "whisper", "current", "online",
                    "login", "logout", "block", "nick",
                    "nickname", "help", "commands", "purge",
                    "reminder"]

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

        if command == "kick":
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
    else:
        # Normal message
        msg = encrypt_few_words(msg)

    length = msg_len(msg.encode())
    return length, msg_type, color, msg


def update_key(force=False):
    """
    :param force: Forces the key update.
    """
    # I made a heroku app, which updates the key every minute.
    global KEY, last_update
    current_time = int(time.time()) * 1000
    if current_time - last_update > 60_000 or force:  # Update time for key
        data = req.get('https://get-api-key-2021.herokuapp.com/').json()
        KEY = data['code']
        last_update = data['last_time']
        print("Updated key to", KEY)


def handle_incoming_command(data, tk_obj):
    global mode
    if data[:7] == "[color]":
        return encrypt_few_words(data[7:], 1)

    elif data.find("Purge") != -1:
        number = int(data.split(' ')[1])
        msg_list = tk_obj.winfo_children()[0].winfo_children()[1]
        purge(number, msg_list)

    elif data[:len("Kicked")] == "Kicked":
        reason = find_end(data, ". ") == 1
        if reason:
            mb.showinfo("Info", f"You've been kicked. "
                                f"Reason: {encrypt_few_words(data[find_end(data, 'Kicked. Reason:')], 2)}")
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

    # nickname change
    # elif data.find("renamed to") != -1:
    #     found_nicks = [x for x in list(search(r"^(.+) renamed to (.+)", data).groups())]
    #     data = f'{found_nicks[0]} renamed to: {found_nicks[1]}'

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
    color = "2c2f33" if color == "NOBGCL" else color
    red = int(f"0x{color[:2]}", 16)
    green = int(f"0x{color[2:4]}", 16)
    blue = int(f"0x{color[4:6]}", 16)
    return "#000000" if red * 0.299 + green * 0.587 + blue * 0.114 > 186 else "#ffffff"


def purge(amount, listbox):
    start = listbox.size() - amount
    if start < 3:
        start = 3
        listbox.delete(start, listbox.size() - 1)
        listbox.insert(tk.END, "Can't delete first 3 messages")
    else:
        listbox.delete(start, listbox.size() - 1)


def receive(tk_obj, client_sock):
    while True:
        update_key()
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
            if msg_type == "SysCmd":
                next_command_size = client_socket.recv(3).decode()
                print("Size: " + next_command_size, end=" | ")

                color = client_sock.recv(6).decode()
                color = "2c2f33" if color == "NOBGCL" else color
                print("Color: " + color, end=" | ")
                # Runs until it hits a command with length 0,
                # Signaling the end of the communication.
                print("Data:")
                while next_command_size != "000":
                    display = client_socket.recv(1).decode()
                    data = client_socket.recv(int(next_command_size)).decode()
                    print(data)
                    # 1 display | 0 don't display
                    if display == '1':
                        msg = handle_incoming_command(data=data, tk_obj=tk_obj)

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
                        print(f"Type: SysCmd | Size: {next_command_size} | Color: {color} | Data: ")
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
            print("But don't worry, we handled it.")
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
    try:
        selection = event.widget.curselection()[0]
        if search(f"^{command_prefix}(whisper)|(w)", entry_field.get()):
            entry_field.delete('0', 'end')
        entry_field.insert(0, f'{command_prefix}whisper {event.widget.get(selection)} ')
    except IndexError:
        pass


def send(input_msg, event=None):
    get = input_msg.get()
    if get == "":
        return
    update_key()
    length, msg_type, color, data = format_message(get.split(" "))
    msg = data
    if not typing_my_name[0]:
        msg = f"{length}{msg_type}{color}{data}"
        print(F"\n\nSent:{msg}\n")
    input_msg.set("")
    if length != "000":
        client_socket.send(msg.encode())


def resize_font(message_list, event=None):
    size = round(event.width / 100) + 4
    size = 5 if size < 6 else size
    try:
        message_list['font'] = ("Varela Round", size)
        message_list.see("end")
    except tk.TclError:
        pass


def chat_room(tk_obj):
    global online_num
    for child in tk_obj.winfo_children():
        child.destroy()
    tk_obj.title("Chatter")
    tk_obj.resizable(width=True, height=True)
    tk_obj.minsize(700, 150)
    tk_obj.attributes("-topmost", True)

    my_msg = tk.StringVar()  # For the messages to be sent.
    my_msg.set("")
    messages_frame = tk.Frame(tk_obj)
    messages_frame.grid(row=0, column=1, columnspan=2, padx=5, pady=10, sticky="ewns")
    scrollbar = tk.Scrollbar(messages_frame)  # To navigate through past messages.
    scrollbar.grid(row=0, column=1, sticky="ewns")

    msg_list = tk.Listbox(messages_frame, height=15, width=75, yscrollcommand=scrollbar.set, background="#2c2f33",
                          foreground="white")
    msg_list.insert(tk.END, "Loading you in. This may take a bit.")
    msg_list.bind('<<ListboxSelect>>', lambda event: listbox_copy(event))

    # Following will contain the messages.
    entry_field = tk.Entry(messages_frame, textvariable=my_msg)
    entry_field.bind("<Return>", lambda x: send(my_msg))
    entry_field.bind('<Control-a>', lambda event: event.widget.select_range(0, 'end'))

    entry_field.grid(row=1, column=1, sticky="wnse")
    send_button = tk.Button(messages_frame, text="Send",
                            command=lambda: send(my_msg), height=2, width=10)
    send_button.grid(row=1, column=1, sticky="ens")

    messages_frame.rowconfigure(0, weight=1)
    messages_frame.columnconfigure(1, weight=1)
    msg_list.grid(row=0, column=1, sticky="ewns")

    # noinspection PyTypeChecker
    online_num[0] = tk.StringVar()
    online_num[0].set("Users online: [Loading...]")

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

    tk_obj.columnconfigure(1, weight=1)
    tk_obj.rowconfigure(0, weight=1)

    tk_obj.protocol("WM_DELETE_WINDOW", lambda: on_closing(tk_obj, my_msg))
    tk_obj.bind("<Configure>", lambda event: resize_font(msg_list, event))


def custom_server_select(tk_obj):
    global current_window
    current_window = 2

    typing_my_name[0] = True
    last_item[0] = 0
    for child in tk_obj.winfo_children():
        child.destroy()
    tk_obj.iconbitmap('./images/list.ico')
    tk_obj.title("Choose Server WAN")
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

    ip_field = EntryWithPlaceholder(tk_obj, "Enter IP")
    ip_field.place(x=275, y=200, width=250, height=45)
    ip_field["font"] = ("Helvetica", 24)

    port_field = EntryWithPlaceholder(tk_obj, "Enter PORT")
    port_field.place(x=275, y=275, width=250, height=45)
    port_field["font"] = ("Helvetica", 24)
    confirm = tk.Button(tk_obj, text="Confirm",
                        command=lambda: confirm_config(tk_obj, ip_field.get(), port_field.get()),
                        font="summer", bd=5)
    confirm.place(x=275, y=345, width=250, height=45)


def join_all(threads, timeout):
    """
    Args:
        threads: a list of thread objects to join
        timeout: the maximum time to wait for the threads to finish
    Raises:
        RuntimeError: is not all the threads have finished by the timeout
    """
    start = cur_time = time.time()
    while cur_time <= (start + timeout):
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=0)
        if all(not t.is_alive() for t in threads):
            break
        time.sleep(0.1)
        cur_time = time.time()
    else:
        print("Force timeout after 5 seconds.")
        #     still_running = [t for t in threads if t.is_alive()]
        #     num = len(still_running)
        #     print(f'Timeout on {num} servers. Removing from list.')


def check_option(item, working_connections):
    check = socket(AF_INET, SOCK_STREAM)
    ip = item[0]
    port = int(item[1])
    try:
        check.connect((ip, port))
    except Exception as e:
        print(f'Timeout: {ip}:{port} - Flagging as inactive.\n')
        req.get(f'https://get-api-key-2021.herokuapp.com/servers/remove/{item[0]}/{item[1]}')
    else:
        working_connections.append([item[0], item[1]])
    finally:
        check.close()


def verify_connections(server_list):
    connections = req.get('https://get-api-key-2021.herokuapp.com').json()['connections']
    working_connections = []
    threads = []
    for item in connections:
        check_thread = Thread(target=lambda: check_option(item, working_connections))
        threads.append(check_thread)
        check_thread.start()

    join_all(threads, 4)
    # force timeout after 4 seconds.

    server_list.delete(0, tk.END)  # delete all users
    for address in working_connections:
        ip = address[0]
        port = address[1]
        server_list.insert(tk.END, f"{ip}:{port}")


def get_selection_confirm(tk_obj, list):
    selection = list.curselection()
    if selection:
        index = selection[0]
        text = list.get(index)
        ip = text[:text.find(":")]
        port = int(text[text.find(":") + 1:])
        print(ip, port)
        confirm_config(tk_obj, ip, port)


def server_list(tk_obj):
    global current_window
    current_window = 2

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

    image1 = Image.open('./images/server_select.png')
    x = image1.resize((800, 450), Image.ANTIALIAS)
    test = ImageTk.PhotoImage(x)
    background = tk.Label(tk_obj, image=test)
    background.image = test
    background["justify"] = "center"
    background.place(x=0, y=0, width=800, height=450)

    server_list = tk.Listbox(tk_obj, height=15, width=75, background="#2c2f33",
                             foreground="white")

    server_list.place(x=180, y=115, width=(660 - 180), height=210)

    verify_connections(server_list)

    refresh = tk.Button(tk_obj, text="Confirm Selection",
                        command=lambda: get_selection_confirm(tk_obj, server_list), height=2, width=10)
    refresh.place(x=400, y=365, width=350, height=80)

    refresh = tk.Button(tk_obj, text="Refresh Servers",
                        command=lambda: verify_connections(server_list), height=2, width=10)
    refresh.place(x=45, y=365, width=350, height=80)


def confirm_config(tk_obj, ip, port):
    global client_socket

    addr = ip, port
    print(f'Connecting to {addr}...')
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect(addr)
    chat_room(tk_obj)
    receive_thread = Thread(target=lambda: receive(tk_obj, client_socket))
    receive_thread.start()


def mode_select(tk_obj):
    global current_window
    current_window = 0

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

    wan_buttom = tk.Button(tk_obj, text="Custom Entry",
                           command=lambda: custom_server_select(tk_obj), height=2, width=10)

    wan_buttom.place(x=80, y=170, width=290, height=150)

    lan_buttom = tk.Button(tk_obj, text="Server list",
                           command=lambda: server_list(tk_obj), height=2, width=10)

    lan_buttom.place(x=410, y=170, width=290, height=150)


if __name__ == "__main__":
    app = tk.Tk()
    mode_select(app)
    app.mainloop()
