import os, sys

def __get_data_dir():

    if sys.platform == "win32":
        return os.path.join(os.getenv("APPDATA"), "Modmanager")
    elif sys.platform == "linux":
        return os.path.expanduser("~/.local/share/Modmanager")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Modmanager")

JSON_REQUEST_TIMEOUT = 10
SEARCH_MAX_ENTRIES = 10
BASE_PATH = __get_data_dir()
INSTANCES_PATH = os.path.join(BASE_PATH, "instances")
ASSETS_PATH = os.path.join(BASE_PATH, "assets")
LIB_PATH = os.path.join(BASE_PATH, "libraries")
META_PATH = os.path.join(BASE_PATH, "meta")

INSTANCES_INDEX = os.path.join(INSTANCES_PATH, "index.json")

THREAD_POOL_WORKERS = 8

# create folders if missing
for folder in [BASE_PATH, INSTANCES_PATH, ASSETS_PATH, LIB_PATH, META_PATH]:
    os.makedirs(folder, exist_ok=True)
os.makedirs(os.path.join(META_PATH, "minecraft"), exist_ok=True)
