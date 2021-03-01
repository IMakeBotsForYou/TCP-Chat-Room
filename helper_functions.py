from threading import Thread, Event
import requests as req
import time
# put here to remove all the imports from server.py and client.py
from socket import AF_INET, socket, SOCK_STREAM, MSG_PEEK, gethostname, gethostbyname
from re import search
import tkinter as tk
from tkinter import messagebox as mb

def post_request(path):
    return req.get("https://get-api-key-2021.herokuapp.com" + path).json()


def join_all(threads, timeout):
    """
    Args:
        threads: a list of thread objects to join
        timeout: the maximum time to wait for the threads to finish
    Raises:
        RuntimeError: is not all the threads have finished by the timeout
    :return Amount of threads who were still active
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
        print(f"Force timeout after {timeout} seconds | ", end="  ")
        return len([t for t in threads if t.is_alive()])


def retrieve_key(last_update, KEY, force=False):
    """
    :param last_update: last time the key was updated, if more than 60 ago, continue
    :param KEY: The key being updated
    :param force: Forces the key update.
    This retrieves key from the heroku key api.
    """
    # I made a heroku app, which updates the key every minute.
    current_time = int(time.time()) * 1000
    if current_time - last_update > 60_000 or force:  # Update time for key
        data = req.get('https://get-api-key-2021.herokuapp.com/').json()
        return data['last_time'], data['code']
    else:
        return last_update, KEY


def msg_len(data):
    """
    :param data: The data we're getting the length of
    :return: Length of the encoded data, left-padded to be 3 digits long.
    """
    return str(len(data)).zfill(3)


def encode(txt, key):
    """
    :param txt: text to encrypt
    :param key: XOR key
    :return: Encrypted text
    """
    return ''.join([chr(ord(a) ^ key) for a in txt])


def call_repeatedly(interval, func, *args):
    """
    Used to check if the user hasn't talked for X seconds.

    :param interval: The interval between the checks
    :param func: Function to run at said interval
    :param args: Arguments for command
    :return: When called, stops the looping.
    """
    stopped = Event()

    def loop():
        x = "continue"
        while not stopped.wait(interval) or x == "stop":  # the first call is in `interval` secs
            x = func(*args)  # if loop asks to stop, stop it

    Thread(target=loop).start()
    return stopped.set
