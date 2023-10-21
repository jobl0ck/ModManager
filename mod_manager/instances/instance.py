import os
from uuid import uuid4
import json
import subprocess
from slugify import slugify
from .. import constants
from ..downloaders import vanilla
from ..downloaders.loaders import forge
from .. import utils
from ..data_structures import MCVersion, MPVersion, Platform, ModLoader
from ..downloaders import ftb

class Instance():

    def __init__(self, uuid : str , data: dict):
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
        print("init start")

        os.makedirs(self.directory, exist_ok=True)
        os.makedirs(os.path.join(self.directory, "minecraft"), exist_ok=True)

        # Download Pack files

        print("pack download start")
        match self.platform:
            case Platform.FEEDTHEBEAST:
                ftb.download(self.mp_version, os.path.join(self.directory, "minecraft"))
                print("Mod Download Done")
            case Platform.CURSEFORGE:
                pass
            case Platform.MODRINTH:
                pass
            case Platform.CUSTOM:
                pass
        
        # Download Vanilla

        #vanilla.download(self.mc_version.mc_version)

        # Download ModLoader
        
        match self.mc_version.loader:
            case ModLoader.FORGE:
                forge.download(self.mc_version.loader_version, self.mc_version.mc_version)
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