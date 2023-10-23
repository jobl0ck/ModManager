from mod_manager import utils
from mod_manager.downloaders import ftb, curseforge, modrinth
from mod_manager.data_structures import MPVersion, MCVersion, ModLoader, Platform
from .instance import Instance

def create_ftb(pack_id : str, version_id : str) -> Instance:

    modpack_manifest = utils.get_json(f"https://api.modpacks.ch/public/modpack/{pack_id}")
    if "status" in modpack_manifest:
        if modpack_manifest["status"] == "error":
            raise AssertionError(modpack_manifest["message"])

    version_manifest = utils.get_json(f"https://api.modpacks.ch/public/modpack/{pack_id}/{version_id}")
    if "status" in version_manifest:
        if version_manifest["status"] == "error":
            raise AssertionError(version_manifest["message"])
    
    game_ver, loader_type, loader_ver = "", "", ""
    for target in version_manifest["targets"]:
        if target["type"] == "modloader":
            loader_type = target["name"]
            loader_ver = target['version']
        elif target["type"] == "game":
            game_ver = target["version"]

    return Instance.create_instance(modpack_manifest["name"], MCVersion(game_ver, loader_type, loader_ver), MPVersion(version_manifest["name"], pack_id, version_id), Platform.FEEDTHEBEAST)

def create_curseforge(pack_id : str, version_id : str) -> Instance:

    modpack_manifest = utils.get_json(f"https://api.modpacks.ch/public/curseforge/{pack_id}")
    if "status" in modpack_manifest:
        if modpack_manifest["status"] == "error":
            raise AssertionError(modpack_manifest["message"])

    version_manifest = utils.get_json(f"https://api.modpacks.ch/public/curseforge/{pack_id}/{version_id}")
    if "status" in version_manifest:
        if version_manifest["status"] == "error":
            raise AssertionError(version_manifest["message"])
    
    game_ver, loader_type, loader_ver = "", "", ""
    for target in version_manifest["targets"]:
        if target["type"] == "modloader":
            loader_type = target["name"]
            loader_ver = target['version']
        elif target["type"] == "game":
            game_ver = target["version"]

    return Instance.create_instance(modpack_manifest["name"], MCVersion(game_ver, loader_type, loader_ver), MPVersion(version_manifest["name"], pack_id, version_id), Platform.CURSEFORGE)