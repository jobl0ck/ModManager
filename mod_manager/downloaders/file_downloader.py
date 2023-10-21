import os
from typing import List, Tuple
from multiprocessing import Pool, Queue, Process
from .. import utils, constants
from ..data_structures import Colors, File

__downloaded_files = Queue()

def download_files(files:List[File]):

    to_download = 0
    for file in files:
        to_download += file.size

    utils.hide_cursor()

    progress_watcher = Process(target=__progress_indicator, args=[to_download])
    progress_watcher.start()

    with Pool(processes=constants.THREAD_POOL_WORKERS) as pool:
        pool.map(__download_file_thread, files)

    progress_watcher.join()
    progress_watcher.close()

    utils.show_cursor()
    print()

def __download_file_thread(file :File):
    global __downloaded_files

    result : Tuple = (False, file, False)
    for url in file.urls:

        try:
            result = download_file(file, url)
            if result[0]:
                break
        except Exception as e:
            print(Colors.END, end="")
            utils.show_cursor()
            raise e

    __downloaded_files.put(result)

def download_file(file : File, url : str|None = None):
        if url == None:
            url = file.urls[0]
        
        os.makedirs(file.dest.removesuffix(file.dest.split(os.sep)[-1]), exist_ok=True)

        success, skipped = utils.download_file(url, file.dest, file.sha1)

        return (success, file, skipped)

def __progress_indicator(to_download):
    global __downloaded_files
    done_downloading = 0
    while done_downloading<to_download:

        success, file, skipped = __downloaded_files.get()

        if not success:

            utils.print_with_progress(file.dest.split("/")[-1] + Colors.RED + " ERROR" + Colors.END, done_downloading/to_download, offset=0)
            to_download -= file.size
            return

        done_downloading += file.size

        statustext = " SKIPPING" if skipped else " OK"

        utils.print_with_progress(file.dest.split("/")[-1] + Colors.GREEN + statustext + Colors.END, done_downloading/to_download, offset=0)
