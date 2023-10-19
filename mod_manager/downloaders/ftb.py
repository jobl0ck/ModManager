import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import Future
from threading import Lock
from ..instances.instance import MPVersion
from .. import utils
from .. import constants

__lock = Lock()

__to_download = 0

__downloads_finished = 0

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
    
    global __downloads_finished, __to_download
    for file in version_manifest["files"]:
        __to_download += file["size"]
    __downloads_finished = 1
    
    try:
        utils.hide_cursor()

        with ThreadPoolExecutor(max_workers=constants.THREAD_POOL_WORKERS) as pool:
            for file in version_manifest["files"]:
                future = pool.submit(__download_fileobj, file, directory)
                future.add_done_callback(__progress_indicator)
        
        utils.show_cursor()
        print()
    except Exception as e:
        utils.show_cursor()
        print(utils.Colors.END, end="")
        raise e

def __progress_indicator(future : Future):
    global __lock, __downloads_finished, __to_download

    result = future.result()

    if not result[0]:

        if result[2] >= 5:
            raise ValueError("Unable to download " + result[1])

        utils.print_with_progress(result[1] + utils.Colors.RED + " ERROR" + utils.Colors.END, __downloads_finished/__to_download, offset=0)
        __to_download -= result[result[3]]
        return
    
    if future.exception():
        utils.show_cursor()
        print(utils.Colors.END, end="")
        print(future.exception())
        sys.exit(1)

    with __lock:
        __downloads_finished += result[3]

        statustext = " SKIPPING" if result[4] else " OK"

        utils.print_with_progress(result[1] + utils.Colors.GREEN + statustext + utils.Colors.END, __downloads_finished/__to_download, offset=0)

def __download_fileobj(file, mc_folder, retry=0):
    dest_path = os.path.join(mc_folder, file["path"])
    os.makedirs(dest_path, exist_ok=True)
    destination = dest_path+file["name"]

    url = file["url"]
    if url == "":
        # bypass curseforge bullshit
        # https://edge.forgecdn.net/files/4367/618/AE2-Things-1.0.5.jar

        urls = [f"https://edge.forgecdn.net/files/{str(file['curseforge']['file'])[0:4]}/{str(file['curseforge']['file'])[4::]}/{file['name']}",
                f"https://www.curseforge.com/api/v1/mods/{str(file['curseforge']['project'])[0:4]}/files/{str(file['curseforge']['file'])}/download"]

        utils.print_with_progress("Start Download of " + file["path"]+file["name"], __downloads_finished/__to_download, offset=0)
        for u in urls:
            success, skipped = utils.download_file(url, destination, file["sha1"])
            if success:
                return (success, os.path.join(file["path"], file["name"]), retry, file["size"], skipped)
            elif "edge.forgecdn.net" in u:
                utils.print_with_progress(f"Download of {file['name']} from {url.split('.')[1:3]} failed, trying fallback if available", __downloads_finished/__to_download, offset=0)

        return (False, os.path.join(file["path"], file["name"]), retry, file["size"], False)

    else:
        utils.print_with_progress("Start Download of " + file["path"]+file["name"], __downloads_finished/__to_download, offset=0)
        success, skipped = utils.download_file(url, destination, file["sha1"])

        return (success, os.path.join(file["path"], file["name"]), retry, file["size"], skipped)
    