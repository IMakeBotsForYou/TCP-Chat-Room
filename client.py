"""Script for Tkinter GUI chat client."""
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
from re import *
import tkinter

# Are we typing name or message?
# Will be used later.
typing_my_name = True

# ----Now comes the sockets part----
HOST = input('Enter host: ')
PORT = input('Enter port: ')

if not HOST:
    # HOST = "213.57.158.173"
    HOST = "10.0.0.24"
if not PORT:
    PORT = 45000
    # PORT = 21567
else:
    PORT = int(PORT)


def encode(txt, key):
    '''
    Encoding / Decoding txt with the chatroom KEY.

    :parameter txt > string
    :parameter key > int
    '''
    return ''.join([chr(ord(a) ^ key) for a in txt])


# Will be used later
name = ""


def receive():
    """Handles receiving of messages."""
    # global name
    while True:
        try:
            msg_list.see("end")
            msg = client_socket.recv(BUFSIZ).decode("utf8")
            n_len = msg.find(":")
            if not n_len == -1:
                msg = encode(msg[:n_len], KEY) + ": " + \
                      encode(msg[n_len+2:], KEY)

            else:
                print(msg)
                if search("has joined the chat!$", msg):
                    temp_name = search("(.+) has joined the chat!$", msg).groups(0)[0]
                    msg = encode(temp_name, KEY) + " has joined the chat!"
                elif search("Nicknamed changed to - ", msg):
                    print("Nickname message")
                    msg = sub(r"\|.+\|" , findall(r"\|.+\|", msg)[0], msg, 1)
                elif search("Welcome", msg):
                    name = search(r"^Welcome (.+)! If you ever want to quit, type \{quit\} to exit.$", msg).groups(0)[0]
                    print(f'NAME: {encode(name, KEY)}')
                    # typing_my_name = False
                    msg = f'Welcome {encode(name, KEY)}! If you ever want to quit, type {quit} to exit'
            msg_list.insert(tkinter.END, msg)
        except OSError:  # Possibly client has left the chat.
            break


KEY = 5


def send(event=None):  # event is passed by binders.
    """Handles sending of messages."""
    get = my_msg.get()

    msg = get
    args = msg.split(" ")
    if not get == "quit()" and not get[0] == "/":  # if not quit, encrypt.
        msg = encode(get, KEY)
# to future me, there is 1 space before the print, fix it :D
    if args[0] == "/nick" or args[0] == "/nickname":
        msg = '/nick ' + encode(msg[msg.find(" "):], KEY)
        msg = ' '.join(list(filter(None, msg.split(" ")))) # remove extra spaces
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

BUFSIZ = 1024

client_socket = socket(AF_INET, SOCK_STREAM)
client_socket.connect(ADDR)

receive_thread = Thread(target=receive)
receive_thread.start()
tkinter.mainloop()  # Starts GUI execution.
