import json
import re
import os
import subprocess
import tempfile
import shutil
import zipfile as zp

from mod_manager.data_structures import File
from mod_manager import constants, utils
from mod_manager.downloaders import vanilla
from mod_manager.downloaders.file_downloader import download_file, download_files

def __get_main_function(jar_path):
    try:
        with zp.ZipFile(jar_path, 'r') as jar_file:
            manifest_data = jar_file.read('META-INF/MANIFEST.MF').decode('utf-8')

        main_class_match = re.search(r'Main-Class:\s*(.*?)\s*\n', manifest_data)

        if main_class_match:
            main_class = main_class_match.group(1)
            return main_class
        else:
            return None

    except (IOError, zp.BadZipFile):
        print(f"Error: Unable to extract manifest from {jar_path}.")
        return None


def __library_to_path(library_name, library_data):
    for lib in library_data["libraries"]:
        if lib["name"] == library_name:
            return lib["downloads"]["artifact"]["path"]
    return None

def transform_maven_string(input_string):
    # de.oceanlabs.mcp:mcp_config:1.18.2-20220404.173914@zip
    # de/oceanlabs/mcp/mcp_config/1.18.2-20220404.173914/mcp_config-1.18.2-20220404.173914.zip
    # de/oceanlabs/mcp/mcp_config/mcp_config-1.18.2-20220404.173914.zip
    # de.oceanlabs.mcp:mcp_config:1.18.2-20220404.173914:mappings-merged@txt

    # Split the input string using ":" and "@" as delimiters
    parts = input_string.split(":")
    
    group, artifact, version = parts[0], parts[1], parts[2]

    path = f"{group.replace('.', os.sep)}{os.sep}{artifact}{os.sep}{version.split('@')[0]}{os.sep}"

    if len(parts) == 4:
        path += f"{artifact}-{version}-{parts[3]}.jar"
    elif "@" in parts[2]:
        version, ext = parts[2].split('@')[0], parts[2].split('@')[1]

        path += f"{artifact}-{version}.{ext}"

    #print(path)

    return os.path.join(constants.LIB_PATH, path)

def __download_v0(install_profile, version_manifest, tempdir, installerpath):
    print("downloading libs")
    vanilla.download_libraries(install_profile, install_profile["version"])
    print("downloading version libs")
    vanilla.download_from_manifest(version_manifest["id"])

    for lib in install_profile["libraries"]:
        lib = lib["downloads"]["artifact"]
        if lib["url"] == "":
            with zp.ZipFile(installerpath) as zf:
                for file in zf.namelist():
                    if lib["path"] in file:
                        source = zf.open(file)
                        target = open(os.path.join(constants.LIB_PATH, lib["path"]), "wb")
                        with source, target:
                            shutil.copyfileobj(source, target)

def __download_v1(install_profile, version_manifest, tempdir):
    side = "client"
    
    print("downloading libs")
    vanilla.download_libraries(install_profile, install_profile["version"])
    print("downloading version libs")
    vanilla.download_from_manifest(version_manifest["id"])

    proc_vars = {}

    proc_vars["MINECRAFT_JAR"] = os.path.join(constants.LIB_PATH, "net", "minecraft", "client", install_profile["minecraft"]+".jar")
    proc_vars["SIDE"] = side

    for name, var in install_profile["data"].items():
        if side in var:
            proc_vars[name] = var[side]
        else:
            raise ValueError("Invalid / unknown data dict structure")


    for proc in install_profile["processors"]:
        if "sides" in proc:
            if not side in proc["sides"]:
                continue
        
        path = __library_to_path(proc["jar"], install_profile)

        success = os.path.exists(os.path.join(constants.LIB_PATH, path)) if path != None else False
        
        #print("[  OK   ]" if success else "[ ERROR ]", path)
        
        if path == None:
            raise FileNotFoundError("Processor not found " + proc["jar"])

        args = []
        for arg in proc["args"]:

            new_arg:str = arg
            for key, val in proc_vars.items():

                placeholder = f"{{{key}}}"
                new_arg = new_arg.replace(placeholder, str(val))
            if new_arg.startswith("/data"):
                new_arg = os.path.join(tempdir, new_arg.removeprefix("/"))
            
            new_arg = re.sub(r'\[([^[\]]*)\]', lambda match: f"{transform_maven_string(match.group(1))}", new_arg)
            #print(new_arg)
            args.append(new_arg)
        
        classpath = []
        classpath.append(os.path.join(constants.LIB_PATH, path))
        for lib in proc["classpath"]:
            lpath = __library_to_path(lib, install_profile)
            if lpath == None: continue
            lpath = os.path.join(constants.LIB_PATH, lpath)
            if os.path.exists(lpath):
                classpath.append(lpath)

        classpath = utils.get_cp_sep().join(classpath)

        subprocess.call(["java", "-cp", classpath, __get_main_function(os.path.join(constants.LIB_PATH, path))] + args)
        


def download(forge_version_name, mc_version_name):
    print("Forge download start")
    tempdir = tempfile.mkdtemp(suffix="modmanager")

    if re.search(r"(1\.10$|1\.9|1\.8|1\.7|1\.6|1\.5|1\.4|1\.3|1\.2|1\.1$)", mc_version_name) is None:
        forge_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version_name}-{forge_version_name}/forge-{mc_version_name}-{forge_version_name}-installer.jar"
    else:
        forge_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version_name}-{forge_version_name}-{mc_version_name}/forge-{mc_version_name}-{forge_version_name}-{mc_version_name}-installer.jar"

    installerpath = os.path.join(tempdir, forge_url.split("/")[-1])

    # download the installer jar
    download_file(File(forge_url, installerpath))

    if not zp.is_zipfile(installerpath): raise zp.BadZipFile("Downloaded installer at " + installerpath + " is not a valid zip file")

    with zp.ZipFile(installerpath) as installer_jar:
        with installer_jar.open("install_profile.json") as f:
            install_profile = json.load(f)
        with installer_jar.open(install_profile["json"].removeprefix(os.sep)) as f:
            version_manifest = json.load(f)
            with open(os.path.join(constants.META_PATH, "minecraft", version_manifest["id"] + ".json"), "w") as f:
                json.dump(version_manifest, f)
        
        for file in installer_jar.namelist():
            if file.startswith("data/"):
                installer_jar.extract(file, tempdir)
    
    if install_profile["spec"] == 0:
        __download_v0(install_profile, version_manifest, tempdir, installerpath)
    elif install_profile["spec"] == 1:
        __download_v1(install_profile, version_manifest, tempdir)

    # delete the installer after finishing
    shutil.rmtree(tempdir)