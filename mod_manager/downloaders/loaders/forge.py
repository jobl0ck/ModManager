import re
import os
import tempfile
from ... import utils


def download(forge_version_name, mc_version_name):
    print(forge_version_name)

    if re.search(r"(1\.10$|1\.9|1\.8|1\.7|1\.6|1\.5|1\.4|1\.3|1\.2|1\.1$)", mc_version_name) is None:
        forge_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version_name}-{forge_version_name}/forge-{mc_version_name}-{forge_version_name}-installer.jar"
    else:
        forge_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version_name}-{forge_version_name}-{mc_version_name}/forge-{mc_version_name}-{forge_version_name}-{mc_version_name}-installer.jar"

    installerpath = os.path.join(tempfile.gettempdir(), forge_url.split("/")[-1])

    # download the installer jar
    utils.download_file(forge_url, installerpath)



    # delete the installer after finishing
    #os.remove(installerpath)    