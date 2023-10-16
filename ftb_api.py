'''

    Api implementation for FTB Modpacks (modpacks.ch)

'''


import os
import hashlib
import subprocess
from concurrent.futures import ThreadPoolExecutor
import re
import json
from slugify import slugify
from api_utils import download_file, get_json
import constants



def search_pack(term: str):
    '''
        Search for a Modpack

        returns tuple (hasfailed, results)
    '''
    try:
        result = get_json(
        f"https://api.modpacks.ch/public/modpack/search/{constants.SEARCH_MAX_ENTRIES}?term={term}"
        )
        if "status" in result:
            if result["status"] == "error":
                return (True, result["message"])
        return (False, result["packs"])
    except Exception:
        return (True, None)



def download_pack(id, version_in=None):
    '''
        Downloads a Modpack From FTB

        returns True on fail
    '''

    version = -1

    modpack_manifest = get_json(f"https://api.modpacks.ch/public/modpack/{id}")
    if "status" in modpack_manifest:
        if modpack_manifest["status"] == "error":
            print(modpack_manifest["message"])
            return True
    for manifest_version in modpack_manifest["versions"][::-1]:
        if not version_in:
            if manifest_version["type"].lower() == "release":
                version = manifest_version["id"]
                break
        else:
            if manifest_version["id"] == version_in:
                version = manifest_version["id"]

    if version == -1:
        return True
    
    version_manifest = get_json(f"https://api.modpacks.ch/public/modpack/{id}/{version}")
    if "status" in version_manifest:
        if version_manifest["status"] == "error":
            print(version_manifest["message"])
            return True
    
    slug = slugify(modpack_manifest["name"])

    with ThreadPoolExecutor(max_workers=constants.THREAD_POOL_WORKERS) as pool:
        for file in version_manifest["files"]:
            pool.submit(download_fileobj, file, slug)

    print("Downloading Mods DONE")

    forgeversion = ""
    mcversion = ""
    
    for target in version_manifest["targets"]:
        if target["name"] == "forge":
            forgeversion = target["version"]
        elif target["name"] == "minecraft":
            mcversion = target["version"]

    if re.search(r"(1\.10$|1\.9|1\.8|1\.7|1\.6|1\.5|1\.4|1\.3|1\.2|1\.1$)", mcversion) is None:
        forge_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mcversion}-{forgeversion}/forge-{mcversion}-{forgeversion}-installer.jar"
    else:
        forge_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mcversion}-{forgeversion}-{mcversion}/forge-{mcversion}-{forgeversion}-{mcversion}-installer.jar"

    dest_path = constants.INSTANCES_BASE+slug+"/loader/"

    os.makedirs(dest_path, exist_ok=True)
    download_file(forge_url, dest_path+"installer.jar")

    subprocess.call(["java", "-jar", dest_path+"installer.jar"])

    profiles = {}

    with open("~/.minecraft/launcher_profiles.json", "rb") as f:
        profiles = json.load(f)
        profiles["profiles"][slug] = {
            
        }


    return False

def download_fileobj(file, packname_slug):
    dest_path = constants.INSTANCES_BASE+packname_slug+"/minecraft/"+file["path"]
    os.makedirs(dest_path, exist_ok=True)
    destination = dest_path+file["name"]
    url = file["url"]
    if url == "":
        # bypass curseforge bullshit
        # https://edge.forgecdn.net/files/4367/618/AE2-Things-1.0.5.jar

        url = f"https://edge.forgecdn.net/files/{str(file['curseforge']['file'])[0:4]}/{str(file['curseforge']['file'])[4::]}/{file['name']}"
    download_file(url, destination)
    with open(destination, "rb") as f:
        error = hashlib.file_digest(f, "sha1").hexdigest() == file["sha1"]
        print(file["name"] + (" OK" if error else " ERROR"))
        return error
