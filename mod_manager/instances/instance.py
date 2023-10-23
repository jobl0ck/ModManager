import os
from platform import release
from typing import List, Literal, Tuple
from uuid import uuid4
import json
import subprocess
import re
from hashlib import sha1
from slugify import slugify
from .. import constants
from ..downloaders import vanilla
from ..downloaders.loaders import forge
from .. import utils
from ..data_structures import MCVersion, MPVersion, Platform, ModLoader
from ..downloaders import ftb, curseforge

class Instance():

    def __init__(self, data: dict):

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
    def load(name : str):
        directory = os.path.join(constants.INSTANCES_PATH, slugify(name))
        if not os.path.exists(directory): return None
        with open(os.path.join(directory, "instance.json"), "r", encoding="utf-8") as f:
            return Instance(json.load(f))
    
    @staticmethod
    def create_instance(name: str, mc_version: MCVersion, mp_version: MPVersion, platform: Platform, load_if_possible:bool = True):
        if load_if_possible:
            try:
                loaded_instance = Instance.load(name)
                if loaded_instance is not None:
                    return loaded_instance
            except FileNotFoundError:
                pass

        directory = os.path.join(constants.INSTANCES_PATH, slugify(name))

        new_instance = Instance({
            "name": name,
            "mc_version": mc_version.to_dict(),
            "mp_version": mp_version.to_dict(),
            "platform":   str(platform),
            "directory":  directory
        })

        new_instance.initialize()

        return new_instance
    
    def save(self):
        os.makedirs(self.directory, exist_ok=True)
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
            case Platform.CURSEFORGE:
                curseforge.download(self.mp_version, os.path.join(self.directory, "minecraft"))
                pass
            case Platform.MODRINTH:
                pass
            case Platform.CUSTOM:
                pass
        
        print("Mod Download Done")
        
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
        # load args

        jvm_args, game_args, libs, main_class, client_id, asset_id = self.__load_manifest()

        jvm_args = self.__parse_arg_rules(jvm_args)
        game_args = self.__parse_arg_rules(game_args)

        classpath = [os.path.join(constants.LIB_PATH, "net", "minecraft", "client", client_id + ".jar")]
        for lib in libs:
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
        
        classpath = utils.get_cp_sep().join(classpath)

        if len(jvm_args) == 0:
            jvm_args = "-XX:+UseG1GC -Dsun.rmi.dgc.server.gcInterval=2147483646 -XX:+UnlockExperimentalVMOptions -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=51 -XX:G1HeapRegionSize=32M".split(" ")

            jvm_args += [
                "-Djava.library.path=${natives_directory}",
                "-Dminecraft.launcher.brand=${launcher_name}",
                "-Dminecraft.launcher.version=${launcher_version}",
                "-cp", "${classpath}",
                "-XX:HeapDumpPath=MojangTricksIntelDriversForPerformance_javaw.exe_minecraft.exe.heapdump",
                "-Xss1M"
            ]

        arg_vars = {
            "natives_directory": os.path.join(constants.NATIVES_DIR, sha1(client_id.encode()).hexdigest()),
            "launcher_name": "Modmanager",
            "launcher_version": "release",
            "classpath": classpath,
            "version_name": client_id,
            "library_directory": constants.LIB_PATH,
            "classpath_separator": utils.get_cp_sep(),
            "auth_player_name": "JoBlock",
            "game_directory": os.path.join(self.directory, "minecraft"),
            "assets_root": constants.ASSETS_PATH,
            "assets_index_name": asset_id,
            "auth_uuid": uuid4(),
            "auth_access_token": "none",
            "clientid": client_id,
            "auth_xuid": "none",
            "user_type": "msa",
            "version_type": "release"
        }

        jvm_args = self.__parse_arg_vars(jvm_args, arg_vars)
        game_args = self.__parse_arg_vars(game_args, arg_vars)

        #print(jvm_args)
        #print(game_args)

        subprocess.run(["java"] + jvm_args + [main_class] + game_args, cwd=os.path.join(self.directory, "minecraft"), check=False)
    
    def __parse_arg_vars(self, args, variables):
        retval = []
        for arg in args:
            new_arg:str = arg
            for key, val in variables.items():

                placeholder = f"${{{key}}}"
                new_arg = new_arg.replace(placeholder, str(val))
            
            retval.append(new_arg)
        
        return retval


    def __parse_arg_rules(self, args : List) -> List[str]:
        new_args = []

        for arg in args:
            if not isinstance(arg, dict):
                new_args.append(arg)
                continue

                
            passed = False
            for rule in arg["rules"]:
                if "os" in rule:
                    ospass = True
                    if "name" in rule["os"]:
                        ospass = ospass and (rule["os"]["name"] == utils.get_sys_platform())
                    
                    if "version" in rule["os"]:
                        from platform import uname
                        ospass = ospass and (re.match(rule["os"]["version"], uname().release))
                    
                    if "arch" in rule["os"]:
                        from platform import machine
                        ospass = ospass and (machine().lower().startswith(rule["os"]["arch"]))
                    
                    passed = ospass
                
            if passed:
                val = arg["value"]
                if isinstance(val, str):
                    new_args.append(val)
                else:
                    for v in val:
                        new_args.append(v)
        
        return new_args
    
    def __load_manifest(self, vname: str|None = None) -> Tuple[List[str], List[str], List[dict], str, str, str]:
        if vname == None:
            match self.mc_version.loader:
                case ModLoader.FORGE:
                    vname = f"{self.mc_version.mc_version}-forge-{self.mc_version.loader_version}"
                case ModLoader.VANILLA:
                    vname = self.mc_version.mc_version
                case _:
                    raise ValueError("Invalid / unsupported loader")
        jvm_args, game_args, libs, main_class, client_id, asset_id = [], [], [], "", "", ""

        with open(os.path.join(constants.META_PATH, "minecraft", vname + ".json"), "r") as f:
            version_manifest = json.load(f)
        if "inheritsFrom" in version_manifest:
            jvm_args, game_args, libs, main_class, client_id, asset_id = self.__load_manifest(version_manifest["inheritsFrom"])
        
        if "arguments" in version_manifest:
            jvm_args += version_manifest["arguments"]["jvm"]
            game_args += version_manifest["arguments"]["game"]
        elif "minecraftArguments" in version_manifest:
            game_args = version_manifest["minecraftArguments"].split(" ")

        if "libraries" in version_manifest:
            libs += version_manifest["libraries"]

        if "mainClass" in version_manifest:
            main_class = version_manifest["mainClass"]
        
        if "downloads" in version_manifest:
            client_id = version_manifest["id"]
        
        if "assets" in version_manifest:
            asset_id = version_manifest["assets"]
        
        
        return jvm_args, game_args, libs, main_class, client_id, asset_id