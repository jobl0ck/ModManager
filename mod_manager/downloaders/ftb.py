import os

from .. import utils
from .file_downloader import download_files
from ..data_structures import Colors, MPVersion, File

def download(mp_version: MPVersion, directory : str):
    version = -1

    modpack_manifest = utils.get_json(f"https://api.modpacks.ch/public/modpack/{mp_version.modpack_id}")
    if "status" in modpack_manifest:
        if modpack_manifest["status"] == "error":
            raise AssertionError(modpack_manifest["message"])
    for manifest_version in modpack_manifest["versions"]:
        if manifest_version["id"] == int(mp_version.version_id):
            version = manifest_version["id"]
            break

    assert version != -1

    version_manifest = utils.get_json(f"https://api.modpacks.ch/public/modpack/{mp_version.modpack_id}/{version}")
    if "status" in version_manifest:
        if version_manifest["status"] == "error":
            raise AssertionError(version_manifest["message"])
   
    to_download= 0
    for file in version_manifest["files"]:
        to_download += file["size"]
    
    try:
        processed_files = []
        for f in version_manifest["files"]:
            

            if "curseforge" in f:
                    urls = __get_curse_urls(f["curseforge"], f["name"])
            else:
                urls = [f["url"]]

            os.makedirs(os.path.join(directory, f["path"]), exist_ok=True)

            processed_files.append(File(
                urls,
                os.path.join(directory, f["path"], f["name"]),
                f["sha1"],
                f["size"],
            ))

        download_files(processed_files)
    except Exception as e:
        utils.show_cursor()
        print(Colors.END, end="")
        raise e

def __get_curse_urls(data : dict[str, str], name : str):

    urls = [f"https://edge.forgecdn.net/files/{str(data['file'])[0:4]}/{str(data['file'])[4::]}/{name}",
            f"https://www.curseforge.com/api/v1/mods/{str(data['project'])[0:4]}/files/{str(data['file'])}/download"]
            
    return urls
    