import os
import math
import re
import requests
import sys
import hashlib
from . import constants

def get_json(url, headers=None):
    if headers:
        return requests.get(url, headers=headers, timeout=constants.JSON_REQUEST_TIMEOUT).json()
    return requests.get(url, timeout=constants.JSON_REQUEST_TIMEOUT).json()

def download_file(url, dest, sha1 : str|None = None, download_if_not_exists = True):
    '''

    returns Tuple (had_success, has_skipped)

    '''
    
    if download_if_not_exists and sha1:
        if os.path.exists(dest):
            with open(dest, "rb") as f:
                if hashlib.file_digest(f, "sha1").hexdigest() == sha1:
                    return (True, True)

    r = requests.get(url, timeout=constants.JSON_REQUEST_TIMEOUT)
    with open(dest, 'wb') as f:
        f.write(r.content)
    
    if sha1:
        if os.path.exists(dest):
            with open(dest, "rb") as f:
                if hashlib.file_digest(f, "sha1").hexdigest() == sha1:
                    return (True, False)
        return (False, False)
    return(True, False)

def print_with_progress(text : str, progress : float, offset=0):
    
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    print(text + " " * (os.get_terminal_size().columns - len(ansi_escape.sub("", text))+offset), end="")

    maxchars = os.get_terminal_size().columns-10
    nr_of_hashtags = math.ceil(maxchars*progress)
    print("[" + ( "#" * nr_of_hashtags) + (" " * (maxchars-nr_of_hashtags)) + f"]{progress*100:>6.2f}%", end="\r")

def hide_cursor():
    print("\x9B\x3F\x32\x35\x6C", end="")

def show_cursor():
    print("\x9B\x3F\x32\x35\x68", end="")

def get_sys_platform():
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "linux":
        return "linux"
    if sys.platform == "darwin":
        return "osx"
    return ""

def get_cp_sep():
    if sys.platform == "win32":
        return ";"
    return ":"