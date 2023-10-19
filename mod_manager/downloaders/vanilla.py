import os
import json
from threading import Lock
from .. import utils
from .. import constants
from .file_downloader import download_file, download_files
from ..data_structures import File

def __find_version(version, manifest_versions):
    for v in manifest_versions:
        if v["id"] == version:
            return v
    return None

def download(version: str):
    print(version)

    versions_manifest = utils.get_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    
    version_manifest_version = __find_version(version, versions_manifest["versions"])
    if not version_manifest_version: raise ValueError("Invalid version")
    version_url = version_manifest_version["url"]

    os.makedirs(os.path.join(constants.META_PATH, "minecraft"), exist_ok=True)
    manifest_path = os.path.join(constants.META_PATH, "minecraft", version + ".json")
    if not os.path.exists(manifest_path):
        download_file(File(version_url, manifest_path))
    

    with open(manifest_path, "r",encoding="utf-8") as f:
        local_manifest = json.load(f)
    
    __download_libraries(local_manifest)

    __download_assets(local_manifest)

    __download_client(local_manifest)


def __download_libraries(manifest : dict):

    files_to_download = []

    for lib in manifest["libraries"]:
        if "rules" in lib:
            do_download = False

            for rule in lib["rules"]:
                if "os" in rule:
                    if "version" in rule["os"]:
                        pass
                    else:

                        if rule["action"] == "allow":
                            action = True
                        elif rule["action"] == "disallow":
                            action = False
                        else:
                            raise ValueError("Unknown action '" + rule["action"] + "'")

                        if rule["os"]["name"] == utils.get_sys_platform():
                            do_download = action
                            
                else:
                    if rule["action"] == "allow":
                        do_download = True
                    elif rule["action"] == "disallow":
                        do_download = False
                    else:
                        raise ValueError("Unknown action '" + rule["action"] + "'")
        
            if not do_download:
                continue
        
        if "artifact" in lib["downloads"]:
            files_to_download.append(File(  lib["downloads"]["artifact"]["url"], 
                                        os.path.join(constants.LIB_PATH, lib["downloads"]["artifact"]["path"]),
                                        lib["downloads"]["artifact"]["sha1"],
                                        lib["downloads"]["artifact"]["size"]  ))
        
        if "natives" in lib:
            if utils.get_sys_platform() in lib["natives"]:
                natives_name = lib["natives"][utils.get_sys_platform()]

                files_to_download.append(File(  lib["downloads"]["classifiers"][natives_name]["url"], 
                                            os.path.join(constants.LIB_PATH, lib["downloads"]["classifiers"][natives_name]["path"]),
                                            lib["downloads"]["classifiers"][natives_name]["sha1"],
                                            lib["downloads"]["classifiers"][natives_name]["size"]  ))
            else:
                print("No natives found for " + lib["name"] + " on " + utils.get_sys_platform())

    download_files(files_to_download)
    print("\nDownloading Libraries Done")
                
        

def __download_assets(manifest : dict):
    os.makedirs(os.path.join(constants.ASSETS_PATH, "indexes"), exist_ok=True)
    path = os.path.join(constants.ASSETS_PATH, "indexes", manifest["assetIndex"]["url"].split(os.sep)[-1])
    download_file(File(manifest["assetIndex"]["url"], path))

    with open(path, "rb") as f:
        assets_manifest = json.load(f)

    assets:dict = assets_manifest["objects"]

    files_to_download = []

    for path, asset in assets.items():
        files_to_download.append(File(
            f"https://resources.download.minecraft.net/{asset['hash'][0:2]}/{asset['hash']}",
            os.path.join(constants.ASSETS_PATH, "objects", asset['hash'][0:2], asset['hash']),
            asset["hash"],
            asset["size"]
        ))
    
    download_files(files_to_download)
    print("\nDownloading Assets Done")


def __download_client(manifest : dict):
    path = os.path.join(constants.LIB_PATH, "minecraft")
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, manifest["id"] + ".jar")
    
    download_file(File(manifest["downloads"]["client"]["url"], file_path, manifest["downloads"]["client"]["sha1"], manifest["downloads"]["client"]["size"]))
    
    print("Downloading Client Done")

