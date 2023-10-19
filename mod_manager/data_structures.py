from enum import Enum
from typing import List

class Platform(Enum):
    FEEDTHEBEAST = "ftb", "Feed The Beast"
    CURSEFORGE = "curse", "Curseforge"
    MODRINTH = "modrinth", "Modrinth"
    CUSTOM = "custom", "Custom"
    UNKNOWN = "unknown", "Unknown Platform"

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, display_name: str = ""):
        self._display_name_ = display_name

    def __str__(self):
        return self.value

    # this makes sure that the display_name is read-only
    @property
    def display_name(self):
        return self._display_name_

class ModLoader(Enum):
    FORGE = "forge", "Forge"
    FABRIC = "fabric", "Fabric"
    VANILLA = "vanilla", "Vanilla"
    UNKNOWN = "unknown", "Unknown Loader"

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, display_name: str = ""):
        self._display_name_ = display_name

    def __str__(self):
        return self.value

    # this makes sure that the display_name is read-only
    @property
    def display_name(self):
        return self._display_name_


class MPVersion():

    def __init__(self, name : str, mid : str, vid : str):
        self.version_name = name
        self.version_id = vid
        self.modpack_id = mid

    @staticmethod
    def from_dict(data: dict):
        return MPVersion(data["name"], data["mid"], data["vid"])
    @staticmethod
    def from_values(name : str, mid : str, vid : str):
        return MPVersion(name, mid, vid)
    
    def to_dict(self) -> dict:
        return {"name": self.version_name, "mid": self.modpack_id, "vid": self.version_id}


class MCVersion():

    def __init__(self, mc_version : str, loader : ModLoader | str, loader_version : str):
        self.mc_version = mc_version
        self.loader = loader if loader is ModLoader else ModLoader(str(loader))
        self.loader_version = loader_version

    @staticmethod
    def from_dict(data : dict):
        return MCVersion(data["mc"], data["loader"], data["loader_version"])
    @staticmethod
    def from_values(mc : str, loader : ModLoader | str, loader_version : str):
        return MCVersion(mc, loader if loader is ModLoader else ModLoader(str(loader)), loader_version)
    
    def to_dict(self) -> dict:
        return {"mc": self.mc_version, "loader": str(self.loader), "loader_version": self.loader_version}

class Colors:
    """ ANSI color codes """
    BLACK = "\033[0;30m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BROWN = "\033[0;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    LIGHT_GRAY = "\033[0;37m"
    DARK_GRAY = "\033[1;30m"
    LIGHT_RED = "\033[1;31m"
    LIGHT_GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    LIGHT_BLUE = "\033[1;34m"
    LIGHT_PURPLE = "\033[1;35m"
    LIGHT_CYAN = "\033[1;36m"
    LIGHT_WHITE = "\033[1;37m"
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    NEGATIVE = "\033[7m"
    CROSSED = "\033[9m"
    END = "\033[0m"
    # cancel SGR codes if we don't write to a terminal
    if not __import__("sys").stdout.isatty():
        for _ in dir():
            if isinstance(_, str) and _[0] != "_":
                locals()[_] = ""
    else:
        # set Windows console in VT mode
        if __import__("platform").system() == "Windows":
            kernel32 = __import__("ctypes").windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            del kernel32

class File():
    def __init__(self, url:str|List[str], dest:str, sha1:str|None = None, size:int = 0) -> None:
        if isinstance(url, str):
            self.urls = [url]
        else:
            self.urls = url
        
        self.dest = dest
        self.sha1 = sha1
        self.size = size