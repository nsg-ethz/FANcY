from bs4 import BeautifulSoup
import requests
import os
import time
import random
import glob
import multiprocessing

from fancy.utils import call_in_path, cwd, merge_pcaps

user_name = ('mail', 'password')


def download_in_path(url, path, auth):
    time.sleep(random.randint(1, 20))
    print("Start Downloading: ", url)
    cmd = 'wget --quiet --user {} --password {} {}'.format(
        auth[0], auth[1], url)
    call_in_path(cmd, path)


# example url
urls = [('', 'https://data.caida.org/datasets/passive-2016/equinix-chicago/', user_name)]


def listLinks(url, auth, ext=''):
    # print url, auth, ext
    page = requests.get(url, auth=requests.auth.HTTPBasicAuth(*auth)).text
    soup = BeautifulSoup(page, 'html.parser')
    return [url + node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]


def rename_pcaps(preamble):

    files_to_rename = [x for x in glob.glob(
        "*") if not x.endswith("anon.pcap")]

    for f in files_to_rename:
        current_name = f
        day = current_name.split("-")[0].strip()
        t = current_name.split("_")[1]
        direction = current_name.split("_")[-1].split(".")[0].strip()
        new_name = "{}.{}.{}-{}.UTC.anon.pcap".format(
            preamble, direction, day, t)
        cmd = "mv {} {}".format(current_name, new_name)
        call_in_path(cmd, ".")


def check_not_downloaded_traces(path_to_check, url):

    with cwd(path_to_check):
        currently_downloaded_traces = glob.glob("*")

    tmp = []
    for x in currently_downloaded_traces:
        if x.endswith(".pcap"):
            tmp.append(x + ".gz")
        elif x.endswith(".pcap.gz"):
            tmp.append(x)

    currently_downloaded_traces = tmp[:]

    to_download = []
    for x in listLinks(url[1], url[2], 'UTC/'):
        for y in listLinks(x, url[2], 'pcap.gz'):
            to_download.append(y)

    to_download = [x.strip().split("/")[-1] for x in to_download]

    not_downloaded = set(to_download).difference(
        set(currently_downloaded_traces))
    return list(not_downloaded)


def unzip_pcaps(path_to_unzip, extension="pcap.gz", num_cores=24):
    with cwd(path_to_unzip):
        files_to_unzip = [x for x in glob.glob("*") if x.endswith(extension)]

    pool = multiprocessing.Pool(num_cores)
    for pcap in files_to_unzip:
        cmd = "gunzip {}".format(pcap)
        pool.apply_async(call_in_path, (cmd, path_to_unzip), {})


def download_missing_traces(path_to_check, url, num_cores=5):
    missing_traces = check_not_downloaded_traces(path_to_check, url)
    pool = multiprocessing.Pool(num_cores)

    url = [url]
    for name, url, auth in url:
        # print name, url, auth
        for first_link in listLinks(url, auth, 'UTC/'):
            links = listLinks(first_link, auth, 'pcap.gz')
            for link in links:
                # check if to download
                if any(link.endswith(x) for x in missing_traces):
                    pool.apply_async(download_in_path,
                                     (link, path_to_check, auth), {})


def merge_same_day_pcaps(path_to_dir="."):

    with cwd(path_to_dir):
        pool = multiprocessing.Pool(2)
        files_to_merge = [x for x in glob.glob(
            "*") if x.endswith("UTC.anon.pcap")]

        # aggregate per day and sort per time, and dir A and B
        same_day_pcaps = {}
        for name in files_to_merge:
            day = name.split(".")[2].split("-")[0].strip()
            if same_day_pcaps.get(day, False):

                same_day_pcaps[day].append(name)
            else:
                same_day_pcaps[day] = [name]

        for element in same_day_pcaps:
            tmp = same_day_pcaps[element][:]
            same_day_pcaps[element] = sorted(tmp, key=lambda x: int(
                x.split("-")[-1].split(".")[0].strip()))

        # sort per dirA and B
        for day, pcaps in same_day_pcaps.iteritems():

            dirA = [x for x in pcaps if 'dirA' in x]
            dirB = [x for x in pcaps if 'dirB' in x]

            if dirA:
                linkName = dirA[0].split(".")[0].strip()
            elif dirB:
                linkName = dirB[0].split(".")[0].strip()
            else:
                continue
            if dirA:
                pool.apply_async(
                    merge_pcaps,
                    (dirA, "{}.dirA.{}.pcap".format(linkName, day)),
                    {})
            if dirB:
                pool.apply_async(
                    merge_pcaps,
                    (dirB, "{}.dirB.{}.pcap".format(linkName, day)),
                    {})


def main(num_cores=5, urls=[]):
    pool = multiprocessing.Pool(num_cores)

    for name, url, auth in urls:
        # print name, url, auth
        os.system("mkdir -p {}".format(name))
        for first_link in listLinks(url, auth, 'UTC/')[:2]:
            print(first_link)
            links = listLinks(first_link, auth, 'pcap.gz')
            for link in links:
                print('downloading: ', link)
                pool.apply_async(download_in_path,
                                 (link, name + "/", auth), {})
