import os
import json
import hashlib
import sys
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock
from .. import utils
from .. import constants

__lock = Lock()

__to_download = 0

__downloads_finished = 0

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

    os.makedirs(os.path.join(constants.META_PATH, "minecraft/"), exist_ok=True)
    manifest_path = os.path.join(constants.META_PATH, "minecraft/", version + ".json")
    if not os.path.exists(manifest_path):
        utils.download_file(version_url, manifest_path)
    

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
            files_to_download.append((  lib["downloads"]["artifact"]["url"], 
                                        lib["downloads"]["artifact"]["path"],
                                        lib["downloads"]["artifact"]["sha1"],
                                        lib["downloads"]["artifact"]["size"]  ))
        
        if "natives" in lib:
            if utils.get_sys_platform() in lib["natives"]:
                natives_name = lib["natives"][utils.get_sys_platform()]

                files_to_download.append((  lib["downloads"]["classifiers"][natives_name]["url"], 
                                            lib["downloads"]["classifiers"][natives_name]["path"],
                                            lib["downloads"]["classifiers"][natives_name]["sha1"],
                                            lib["downloads"]["classifiers"][natives_name]["size"]  ))
            else:
                print("No natives found for " + lib["name"] + " on " + utils.get_sys_platform())

    global __downloads_finished, __to_download
    __downloads_finished = 1
    __to_download = 0

    for file in files_to_download:
        __to_download += file[3]

    utils.hide_cursor()

    utils.print_with_progress("Starting Download of Libraries...", 0.0)

    with ThreadPoolExecutor(max_workers=constants.THREAD_POOL_WORKERS) as pool:
        for file in files_to_download:
            future = pool.submit(__download_file, file[0], file[1], file[2], file[3])
            future.add_done_callback(__progress_indicator)
    
    utils.show_cursor()
    print("\nDownloading Libraries Done")
                
        

def __download_assets(manifest : dict):
    os.makedirs(os.path.join(constants.ASSETS_PATH, "indexes"), exist_ok=True)
    path = os.path.join(constants.ASSETS_PATH, "indexes", manifest["assetIndex"]["url"].split("/")[-1])
    utils.download_file(manifest["assetIndex"]["url"], path)

    with open(path, "rb") as f:
        assets_manifest = json.load(f)

    assets:dict = assets_manifest["objects"]

    files_to_download = []

    for path, asset in assets.items():
        files_to_download.append((
            f"https://resources.download.minecraft.net/{asset['hash'][0:2]}/{asset['hash']}",
            os.path.join(constants.ASSETS_PATH, "objects", asset['hash'][0:2], asset['hash']),
            asset["hash"],
            asset["size"]
        ))
    
    global __downloads_finished, __to_download
    __downloads_finished = 1
    __to_download = 0

    for file in files_to_download:
        __to_download += file[3]

    utils.hide_cursor()

    utils.print_with_progress("Starting Download of Assets...", 0.0)

    from time import sleep

    with ThreadPoolExecutor(max_workers=constants.THREAD_POOL_WORKERS) as pool:
        for file in files_to_download:
            future = pool.submit(__download_file, file[0], file[1], file[2], file[3])
            future.add_done_callback(__progress_indicator)
    
    utils.show_cursor()
    print("\nDownloading Assets Done")


def __download_client(manifest : dict):
    path = os.path.join(constants.LIB_PATH, "minecraft")
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, manifest["id"] + ".jar")
    
    __download_file(manifest["downloads"]["client"]["url"], file_path, manifest["downloads"]["client"]["sha1"], manifest["downloads"]["client"]["size"])
    
    print("Downloading Client Done")


def __download_file(url, dest, sha1, size):
    path = os.path.join(constants.LIB_PATH, dest)
    dir_path = path.removesuffix(path.split("/")[-1])
    os.makedirs(dir_path, exist_ok=True)

    success, skipped = utils.download_file(url, path)
    return (success, path, size, skipped)
    
def __progress_indicator(future : Future):
    global __lock, __downloads_finished, __to_download

    result = future.result()

    if not result[0]:

        utils.print_with_progress(result[1] + utils.Colors.RED + " ERROR" + utils.Colors.END, __downloads_finished/__to_download, offset=0)
        with __lock:
            __to_download -= result[result[3]]
        return
    
    if future.exception():
        utils.show_cursor()
        print(utils.Colors.END, end="")
        print(future.exception())
        sys.exit(1)

    with __lock:
        __downloads_finished += result[2]

    statustext = " SKIPPING" if result[3] else " OK"

    utils.print_with_progress(result[1] + utils.Colors.GREEN + statustext + utils.Colors.END, __downloads_finished/__to_download, offset=0)
