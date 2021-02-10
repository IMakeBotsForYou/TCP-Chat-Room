"""Script for Tkinter GUI chat client."""
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
from re import search

import tkinter as tk
from tkinter import messagebox as mb
from PIL import ImageTk, Image
import requests as req
import time

last_item = 0
# Are we typing name or message?
typing_my_name = True
command_prefix = "/"
# ----Now comes the sockets part----
HOST = "0"
PORT = 0

addr = (0, 0)

my_msg = 0  # For the messages to be sent.
client_socket = socket(AF_INET, SOCK_STREAM)
top = 0
msg_list = 0
BUFFER_SIZE = 1024
last_update = 0  # last key update
# Will be used later
name = ""


def encode(txt, key):
    return ''.join([chr(ord(a) ^ key) for a in txt])


def leave_server(a):
    """
    :param a: Root TKinter object
    """
    client_socket.close()
    a = ServerSelect(a)


def handle_message(msg):
    # Welcome message
    """
    :param msg: The message being handled
    Takes parameter msg. This function figures out what do to with said message.
    It can either be a message from another user, or from the System. So first,
    we figure out if it's a message from the system, requiring special care.
    Examples are:
        - Kicked
        - Direct Message
        - User left server
    """
    global top
    if search(r"^{System}", msg):
        msg = msg[len("{System} "):]
        if msg == "Kindly, leave":
            leave_server(top)

        if msg == "Kicked":
            mb.showinfo("Instructions", "You've been kicked! Oh no!")
            leave_server(top)

        if search("Direct message to: ", msg):
            msg = encrypt_few_words(msg, 5)
        if search("Message from ", msg):
            msg = msg[:14 + 8] + msg[14 + 8:msg.find(":")] + ": " + encode(msg[msg.find(":") + 2:], KEY)
        if search("Command List", msg):
            msg = msg[len("Command List") + 1:]

        # Nickname
        elif search("changed to", msg):
            found_nicks = [x for x in list(search(r"^(.+) changed to (.+)", msg).groups())]
            msg = "{System} " + f'{found_nicks[0]} renamed to: {found_nicks[1]}'

        # Users Online
        elif search(r"\d+ users online", msg):
            before = msg[:msg.find("online") + len("online")] + " "
            after = " | ".join([x for x in msg[len(before) + 1:].split(" | ")])
            msg = before + after

        # On user leave
        elif search("left the chat", msg):
            user_name = search(r'^(.+) has left the chat.$', msg).groups()[0]
            print(f'LEFT CHAT: {user_name}')
            msg = "{System} " + f'{user_name} has left the chat.'
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
        print("Updated key to ", KEY)


def receive():
    """Handles receiving of messages."""
    global top, last_item
    while True:
        update_key()
        try:
            msg_list.see("end")
            msg = client_socket.recv(BUFFER_SIZE).decode("utf8")
            n_len = msg.find(":")
            if msg == "What is the key?":
                client_socket.send(bytes(str(KEY), "utf8"))
                msg = "Logging in as Admin..."

            elif not n_len == -1 and not search(r"^{System}", msg):
                update_key()
                msg = msg[:n_len] + ": " + encode(msg[n_len + 2:], KEY)
            else:
                msg = handle_message(msg)

            for line in msg.split("\n"):
                msg_list.insert(tk.END, line)
                last_item += 1
                if search("@" + name, line):
                    msg_list.itemconfig(last_item, bg='yellow')
        except OSError:  # Possibly client has left the chat.
            break


KEY = 5


def encrypt_few_words(msg, start=0, end=-1):
    args = msg.split(" ")
    end = end if end != -1 else len(args) - 1
    for i in range(start, end + 1):
        args[i] = encode(args[i], KEY)
    return ' '.join(args)


def command_handler(msg, args):
    global name
    if not msg == "quit()" and not msg[0] == command_prefix and not typing_my_name:
        '''
        #   Normal Message
        '''
        msg = encode(msg, KEY)

    elif msg[0] == command_prefix and not typing_my_name:
        '''
        #   Commands
        '''
        args[0] = args[0][1:]
        two_args_commands = ["w", "whisper", "kick", "ban"]
        one_arg_commands = ["announce", "bold", "login"]
        if args[0] in two_args_commands:
            # commands that use 2 arguments
            msg = encrypt_few_words(msg, 2)
        elif args[0] in one_arg_commands:
            # commands that use one argument
            msg = encrypt_few_words(msg, 1)
        else:
            # nickname command
            name = '_'.join(args[1:])
            msg = f'/{args[0]} {name}' if f'{command_prefix}{args[0]}' in ["/nick", "/nickname"] else msg
        msg = ' '.join(list(filter(None, msg.split(" "))))  # remove extra spaces
    return msg


def send(event=None):  # event is passed by binders.
    """Handles sending of messages.
    :type event: object
    """
    global KEY, typing_my_name, command_prefix
    get = my_msg.get()
    if get == "":
        return
    update_key()
    msg = command_handler(get, get.split(" "))

    my_msg.set("")  # Clears input field.
    client_socket.send(bytes(msg, "utf8"))
    typing_my_name = False


def on_closing(event=None):
    """This function is to be called when the window is closed."""
    my_msg.set("quit()")
    send()


def confirm_config(x, ip, port):
    global addr, my_msg, client_socket, top, msg_list, BUFFER_SIZE
    if ip == "" or "Enter IP":
        ip = "79.177.33.79"
        # ip = "10.0.0.12"
    if port == "" or "Enter PORT":
        port = 45000
    addr = ip, port
    print(f'Connecting to {addr}...')

    x.destroy()
    top = tk.Tk()
    top.title("Chatter")
    top.minsize(500, 150)
    top.attributes("-topmost", True)

    my_msg = tk.StringVar()  # For the messages to be sent.
    messages_frame = tk.Frame(top)

    my_msg.set("")
    scrollbar = tk.Scrollbar(messages_frame)  # To navigate through past messages.
    # Following will contain the messages.
    msg_list = tk.Listbox(messages_frame, height=15, width=75, yscrollcommand=scrollbar.set)
    scrollbar.grid(row=0,column=1, sticky="ewns")
    msg_list.insert(tk.END, "Loading you in. This may take a bit.")

    messages_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="ewns")
    top.columnconfigure(0, weight=1)
    top.rowconfigure(1, weight=1)

    messages_frame.rowconfigure(0, weight=1)
    messages_frame.columnconfigure(0, weight=1)

    msg_list.grid(row=0, column=0, sticky="ewns")

    entry_field = tk.Entry(messages_frame, textvariable=my_msg)
    entry_field.bind("<Return>", send)
    entry_field.grid(row=1, column=0, sticky="wnse")
    send_button = tk.Button(messages_frame, text="Send", command=send, height=2,width=10)
    send_button.grid(row=1, column=0, sticky="ens")
    top.protocol("WM_DELETE_WINDOW", "on_closing")

    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect(addr)

    receive_thread = Thread(target=receive)
    receive_thread.start()
    top.mainloop()


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


class ServerSelect:
    def __init__(self, tk_obj):
        # setting title
        tk_obj.title("Choose Server")
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
        ip_field["font"] = ("Courier", 20)

        port_field = EntryWithPlaceholder(tk_obj, "Enter PORT")
        port_field.place(x=275, y=275, width=250, height=45)
        port_field["font"] = ("Courier", 24)
        confirm = tk.Button(tk_obj, text="Confirm", command=lambda: confirm_config(tk_obj,
                                                                                   ip_field.get(),
                                                                                   port_field.get()),
                            font="summer", bd=5)
        confirm.place(x=275, y=345, width=250, height=45)


if __name__ == "__main__":
    root = tk.Tk()
    app = ServerSelect(root)
    root.mainloop()
