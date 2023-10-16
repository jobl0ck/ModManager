from enum import Enum
import os
from uuid import uuid4
import json
import subprocess
from slugify import slugify
from .. import constants
from ..downloaders import vanilla
from .. import utils

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
    def __init__(self, _: str, display_name: str = None):
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
    def __init__(self, _: str, display_name: str = None):
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

    def __init__(self, mc_version : str, loader : str, loader_version : str):
        self.mc_version = mc_version
        self.loader = loader
        self.loader_version = loader_version

    @staticmethod
    def from_dict(data : dict):
        return MCVersion(data["mc"], data["loader"], data["loader_version"])
    @staticmethod
    def from_values(mc : str, loader : str, loader_version : str):
        return MCVersion(mc, loader, loader_version)
    
    def to_dict(self) -> dict:
        return {"mc": self.mc_version, "loader": self.loader, "loader_version": self.loader_version}
        

class Instance():

    def __init__(self, uuid : str , data: dict) -> dict:
        self.uuid = uuid

        self.mp_name = data["name"]

        self.mc_version = MCVersion.from_dict(data["mc_version"])
        try:
            self.platform = Platform(data["platform"])
        except ValueError:
            self.platform = Platform.UNKNOWN

        self.mp_version = MPVersion.from_dict(data["mp_version"])

        self.directory = os.path.expanduser(data["directory"])
    
    def to_dict(self) -> dict:
        return {
            "name": self.mp_name,
            "mc_version": self.mc_version.to_dict(),
            "mp_version": self.mp_version.to_dict(),
            "platform": str(self.platform),
            "directory": self.directory,
        }
    
    @staticmethod
    def create_instance(name: str, mc_version: MCVersion, mp_version: MPVersion, platform: Platform):
        directory = os.path.join(constants.INSTANCES_PATH, slugify(name))

        new_instance = Instance(str(uuid4()), {
            "name": name,
            "mc_version": mc_version.to_dict(),
            "mp_version": mp_version.to_dict(),
            "platform":   str(platform),
            "directory":  directory
        })

        new_instance.initialize()

        return new_instance
    
    def save(self):

        with open(os.path.join(self.directory, "instance.json"), "w", encoding="utf-8") as f:
            f.truncate()
            json.dump(self.to_dict(), f)
            

    def initialize(self):

        os.makedirs(self.directory, exist_ok=True)
        os.makedirs(os.path.join(self.directory, "minecraft"), exist_ok=True)

        # Download Pack files

        match self.platform:
            case Platform.FEEDTHEBEAST:
                from ..downloaders import ftb
                ftb.download(self.mp_version, os.path.join(self.directory, "minecraft"))
                print("Mod Download Done")
            case Platform.CURSEFORGE:
                pass
            case Platform.MODRINTH:
                pass
            case Platform.CUSTOM:
                pass
        
        # Download Vanilla

        vanilla.download(self.mc_version.mc_version)

        # Download ModLoader

        match self.mc_version.loader:
            case ModLoader.FORGE:
                pass
            case ModLoader.FABRIC:
                pass

        self.save()
        print("initialized " + self.mp_name)
    
    def launch(self):

        classpath = []

        with open(os.path.join(constants.META_PATH, "minecraft", self.mc_version.mc_version + ".json"), "r", encoding="utf-8") as f:
            manifest = json.load(f)
            for lib in manifest["libraries"]:
                if "artifact" in lib["downloads"]:
                    path = os.path.join(constants.LIB_PATH, lib["downloads"]["artifact"]["path"])
                    if os.path.exists(path):
                        classpath.append(path)
                if "natives" in lib:
                    if utils.get_sys_platform() in lib["natives"]:
                        natives_name = lib["natives"][utils.get_sys_platform()]
                        path = os.path.join(constants.LIB_PATH, lib["downloads"]["classifiers"][natives_name]["path"])
                        if os.path.exists(path):
                            classpath.append(path)

        classpath.append(os.path.join(constants.LIB_PATH, "minecraft", self.mc_version.mc_version + ".jar"))

        subprocess.run(["java", "-Djava.library.path=" + constants.LIB_PATH,
                                "-Dminecraft.launcher.brand=" + "modmanager",
                                "-Dminecraft.launcher.version=" + "release",
                                "-cp", ":".join(classpath),
                                "-Xss1M",
                                manifest["mainClass"],
                                "--username", "JoBlock",
                                "--version",  self.mc_version.mc_version,
                                "--accessToken", "null",
                                "--gameDir", self.directory,
                                "--assetsDir", constants.ASSETS_PATH,
                                "--assetIndex", manifest["assets"]], check=False, cwd=self.directory)