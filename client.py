"""Script for Tkinter GUI chat client."""
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
from re import search, sub
import tkinter

# Are we typing name or message?
# Will be used later.
typing_my_name = True

# ----Now comes the sockets part----
HOST = input('Enter host: ')
PORT = input('Enter port: ')

if not HOST:
    # HOST = "213.57.158.173"
    HOST = "109.64.93.54"
if not PORT:
    PORT = 45000
    # PORT = 21567
else:
    PORT = int(PORT)


def encode(txt, key):
    return ''.join([chr(ord(a) ^ key) for a in txt])


# Will be used later
name = ""


def handle_message(msg):
    # Welcome message
    if search(r"^\{System}", msg):
        if search("Direct message to: ", msg):
            msg = msg[:28] + encode(msg[28:msg.find("-")-1], KEY) + ": " + ' '.join([encode(x, KEY) for x in: msg[28 + len(msg[28:msg.find("-")-1])+3:].split(" ")])
        if search("Message from ", msg):
            msg = msg[:14 + 8] + encode(msg[14 + 8:msg.find(":")], KEY) + ": " + encode(msg[msg.find(":") + 2:], KEY)
        if search("Command List", msg):
            msg = "Command List:\n" \
                  "/nick <new name>: Rename Yourself!\n" \
                  "/whisper <name>: whisper to someone\n" \
                  "/online: show who's online!\n"
        elif search("has joined the chat!$", msg):
            temp_name = search("{System} (.+) has joined the chat!$", msg).groups()[0]
            msg = encode(temp_name, KEY) + " has joined the chat!"

        # Nickname
        elif search("changed to", msg):
            found_nicks = [encode(x, KEY) for x in list(search(r"^{System} (.+) changed to (.+)", msg).groups())]
            msg = "{System} " + f'{found_nicks[0]} renamed to: {found_nicks[1]}'

        # Users Online
        elif search(r"\d+ users online", msg):
            before = msg[:msg.find("online") + len("online")] + " "
            after = " | ".join([encode(x, KEY) for x in msg[len(before) + 1:].split(" | ")])
            msg = before + after

        # Self-Welcome
        elif search("Welcome", msg):
            user_name = search(r"Welcome (.+)! If you ever want to quit, type {quit} to exit.$", msg).groups()[0]
            print(f'NAME: {encode(user_name, KEY)}')
            # typing_my_name = False
            msg = f'Welcome {encode(user_name, KEY)}! If you ever want to quit, type {quit} to exit'

        # On user leave
        elif search("left the chat", msg):
            user_name = search(r'^{System} (.+) has left the chat.$', msg).groups()[0]
            print(f'LEFT CHAT: {encode(user_name, KEY)}')
            # typing_my_name = False
            msg = "{System} " + f'{encode(user_name, KEY)} has left the chat.'
    return msg


def receive():
    """Handles receiving of messages."""
    # global name
    while True:
        try:
            msg_list.see("end")
            msg = client_socket.recv(BUFFER_SIZE).decode("utf8")
            n_len = msg.find(":")
            if not n_len == -1 and not search(r"^{System}", msg):
                msg = encode(msg[:n_len], KEY) + ": " + \
                      encode(msg[n_len + 2:], KEY)
            else:
                msg = handle_message(msg)
            msg_list.insert(tkinter.END, msg)
        except OSError:  # Possibly client has left the chat.
            break


KEY = 5


def send(event=None):  # event is passed by binders.
    """Handles sending of messages.
    :type event: object
    """
    get = my_msg.get()
    if get == "":
        return
    msg = get
    args = msg.split(" ")

    if not get == "quit()" and not get[0] == "/":
        msg = encode(get, KEY)

    elif get[0] == "/":
        print("Command registered", args[0][1:])
        print(args[1:])
        msg = args[0] + " " + encode(' '.join(args[1:]), KEY).replace(encode(" ", KEY), " ")
        msg = ' '.join(list(filter(None, msg.split(" "))))  # remove extra spaces

    my_msg.set("")  # Clears input field.
    client_socket.send(bytes(msg, "utf8"))

    if msg == "quit()":
        client_socket.close()
        top.quit()


def on_closing(event=None):
    """This function is to be called when the window is closed."""
    my_msg.set("quit()")
    send()


ADDR = (HOST, PORT)

top = tkinter.Tk()

top.title("Chatter")
top.attributes("-topmost", True)
messages_frame = tkinter.Frame(top)
my_msg = tkinter.StringVar()  # For the messages to be sent.
my_msg.set("")
scrollbar = tkinter.Scrollbar(messages_frame)  # To navigate through past messages.
# Following will contain the messages.
msg_list = tkinter.Listbox(messages_frame, height=15, width=75, yscrollcommand=scrollbar.set)
scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
msg_list.pack(side=tkinter.LEFT, fill=tkinter.BOTH)

msg_list.pack()
messages_frame.pack()

entry_field = tkinter.Entry(top, textvariable=my_msg)
entry_field.bind("<Return>", send)
entry_field.pack()
send_button = tkinter.Button(top, text="Send", command=send)
send_button.pack()
top.protocol("WM_DELETE_WINDOW", on_closing)

HOST = ""
PORT = 0

BUFFER_SIZE = 1024

client_socket = socket(AF_INET, SOCK_STREAM)
client_socket.connect(ADDR)

receive_thread = Thread(target=receive)
receive_thread.start()
tkinter.mainloop()  # Starts GUI execution.
