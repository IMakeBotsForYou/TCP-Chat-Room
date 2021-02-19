"""Script for Tkinter GUI chat client."""
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
from re import search
import tkinter as tk
from tkinter import messagebox as mb
from PIL import ImageTk, Image
import requests as req
import time
from pyperclip import copy

# ----Functionality---- #
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

    def foc_in(self, *args):
        if self['fg'] == self.placeholder_color:
            self.delete('0', 'end')
            self['fg'] = self.default_fg_color

    def foc_out(self, *args):
        if not self.get():
            self.put_placeholder()


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
    if last_item[0] != 0 and messenger and not typing_my_name[0]:
        messenger.set("quit()")
        send(messenger)
    elif typing_my_name[0] and last_item[0] != 0:
        select_server(tk_obj)
    else:
        tk_obj.destroy()


def handle_message(msg, tk_obj):
    # Welcome message
    """
    :param msg: The message being handled
    :param tk_obj: The tk form object.
    Takes parameter msg. This function figures out what do to with said message.
    It can either be a message from another user, or from the System. So first,
    we figure out if it's a message from the system, requiring special care.
    Examples are:
        - Kicked
        - Direct Message
        - User left server
    """
    args = msg.split(" ")
    print(f"msg: {msg}")
    if search(r"^{System}", msg):

        msg = msg[len("{System} "):]
        if msg.find("Kicked") != -1:
            end = find_end(msg, ". ")  # Reason for kick was provided

            if end == 1:
                mb.showinfo("Instructions", "You've been kicked! Oh no!")
                print("No reason")
            else:
                mb.showinfo("Instructions", f'{encrypt_few_words(msg[end:], 1)}')
            select_server(tk_obj)

        elif msg.find("was kicked by") != -1:
            x = msg.find("{System}")
            x = len(msg) if x == -1 else x
            msg = msg[:x]
            if len(args) > 6:
                msg = encrypt_few_words(msg, 6)  # name was kicked by name for (args[6] + )

        elif search("Welcome", msg):
            typing_my_name[0] = False  # Valid name

        if search("Update user_num", msg):
            online_member_number_but_its_an_int[0] = int(msg[msg.find(",")+1:msg.find("{System}")])
            online_num[0].set(f'Users online: {online_member_number_but_its_an_int}')

            msg = msg[find_end(msg, "{System} "):]

            members = msg[14:].split("+")
            names = tk_obj.winfo_children()[1].winfo_children()[1]

            names.delete(0, tk.END)  # delete all users

            for member in members:
                print("add", member)  # add them back with new user / nickname
                names.insert(tk.END, member)
            msg = "don't" if not search("changed to", msg) else msg
            # if we need to update bc a nickname change, keep checking the message

        elif search("Direct message to: ", msg):
            msg = encrypt_few_words(msg, 5)

        elif search("Message from ", msg):
            msg_array = msg[find_end(msg, args[3]) + 1:].split(" ")
            msg = f'{msg[:find_end(msg, args[3])]} {" ".join([encode(x, KEY) for x in msg_array])}'
        elif search("Command List", msg):
            msg = msg[len("Command List") + 1:]

        # Nickname
        if search("changed to", msg):
            found_nicks = [x for x in list(search(r"^(.+) changed to (.+)", msg).groups())]
            msg = "{System} " + f'{found_nicks[0]} renamed to: {found_nicks[1]}'

        # Users Online
        elif search(r"\d+ users online", msg):
            before = msg[:msg.find("online") + len("online")] + " , "
            after = " | ".join([x for x in msg[len(before) + 1:].split(" | ")])
            msg = before + after

        elif search(r"Not a valid command", msg):
            msg = "Invalid Command."

        # On user leave
        elif search("left the chat", msg):
            try:
                user_name = search(r'^(.+) has left the chat.$', msg).groups()[0]
                print(f'LEFT CHAT: {user_name}')
                msg = "{System} " + f'{user_name} has left the chat.'
            except AttributeError:
                pass
        else:
            msg = msg
    else:
        if msg.find("Kindly, leave") != -1:
            select_server(tk_obj)
    return msg


def encrypt_few_words(msg, start=0, end=-1):
    global KEY
    args = msg.split(" ")
    end = end if end != -1 else len(args) - 1
    for i in range(start, end + 1):
        args[i] = encode(args[i], KEY)
    return ' '.join(args)


def command_handler(msg, args):
    global name
    msg = ' '.join(list(filter(None, args)))  # remove extra spaces
    args = list(filter(None, args))  # remove extra spaces
    if not msg == "quit()" and not msg[0] == command_prefix and not typing_my_name[0]:
        '''
        #   Normal Message
        '''
        msg = encode(msg, KEY)

    elif msg[0] == command_prefix and not typing_my_name[0]:
        '''
        #   Commands
        '''
        args[0] = args[0][1:]
        two_args_commands = ["w", "whisper", "kick", "ban"]
        one_arg_commands = ["announce", "bold", "login", "block"]

        if args[0] in two_args_commands:
            # commands that use 2 arguments
            if len(args) < 3 and args[0] not in ["kick", "ban"]:
                msg = f"{command_prefix}usage_{args[0]}"
            else:
                msg = encrypt_few_words(msg, 2)

        elif args[0] in one_arg_commands:
            # commands that use one argument
            if len(args) < 2:
                msg = f"{command_prefix}usage_{args[0]}"
            else:
                msg = encrypt_few_words(msg, 1)
        else:
            # nickname command
            name = '_'.join(args[1:])
            msg = f'{command_prefix}{args[0]} {name}' if f'{command_prefix}{args[0]}' in \
                                                         [f"{command_prefix}nick", f"{command_prefix}nickname"] \
                                                         else msg
        msg = ' '.join(list(filter(None, msg.split(" "))))
        # remove extra spaces again,
        # in case it sucked the first time
    else:
        name = "_".join(args)

    return msg


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


def receive(tk_obj, client_sock):
    while True:
        update_key()
        try:
            msg_list = tk_obj.winfo_children()[0].winfo_children()[1]
            msg_list.see("end")
            # accessing all the damn frames and that
            msg = client_sock.recv(BUFFER_SIZE).decode("utf8")
            # find length of username if there is one
            n_len = msg.find(':')
            if not n_len == -1 and not search(r"^{System}", msg):
                update_key()
                msg = msg[:n_len] + ": " + encode(msg[n_len + 2:], KEY)
            else:
                msg = handle_message(msg, tk_obj)

            if msg != "Kindly, leave":
                for line in msg.split("\n"):
                    if msg != "don't":
                        try:
                            msg_list.insert(tk.END, line)
                            last_item[0] += 1
                        except tk.TclError:  # server closed
                            pass
                    if line.find(f'@{name}') != -1:
                        msg_list.itemconfig(last_item[0], bg='#C28241')
        except OSError:
            break  # Client has left the chat
        except IndexError:
            break  # Client has left the chat
        except RuntimeError:
            break  # Client has left the chat


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
    msg = command_handler(get, get.split(" "))
    input_msg.set("")
    client_socket.send(bytes(msg, "utf8"))


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


def select_server(tk_obj):
    typing_my_name[0] = True
    last_item[0] = 0
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

    image1 = Image.open("./images/bg.png")
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


def confirm_config(tk_obj, ip, port):
    global client_socket
    if ip == "" or "Enter IP":
        ip = "79.177.33.79"
        # ip = "10.0.0.12"
    if port == "" or "Enter PORT":
        port = 45000
    addr = ip, port
    print(f'Connecting to {addr}...')
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect(addr)
    chat_room(tk_obj)
    receive_thread = Thread(target=lambda: receive(tk_obj, client_socket))
    receive_thread.start()


if __name__ == "__main__":
    app = tk.Tk()
    select_server(app)
    app.mainloop()
