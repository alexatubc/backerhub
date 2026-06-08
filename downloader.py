from pykraken.kraken import Kraken
import pixeldrain_reloaded as pixeldrain
import sqlite3
from constants import *
import requests
import re
from os.path import splitext
from shutil import copyfileobj
from os import makedirs

"""
Count of links used to host files in Trackerhub
18594 pillows.su
 2758 pixeldrain.com
 2399 krakenfiles.com
 2316 pillowcase.su
 1878 imgur.gg
  789 drive.google.com
"""

# parent_dir comes from gui.py
PARENT_DIR = 'example'

def main():
    # temporary, list of links (maybe with associated names) should come from gui.py
    connection = sqlite3.connect('TrackerHub.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM Links')
    link_table = cursor.fetchall()

    for row in link_table:
        link = row[2]
        try:
            file_hoster = find_file_hoster(link)
            download_file(link, PARENT_DIR, file_hoster, cursor)
        except Exception as e:
            print(f'Failed to download {link}: {e}')


def find_file_hoster(link: str) -> str:
    domain = link.split('//')[1].split('/')[0]
    if 'pillow' in domain:
        return 'pillowcase'
    elif 'kraken' in domain:
        return 'krakenfiles'
    elif 'pixeldrain' in domain:
        return 'pixeldrain'
    else:
        return 'unrecognized domain'


def download_file(link: str, parent_dir: str, file_hoster: str, cursor):
    cursor.execute('''
        SELECT Artists.name, Tracks.era, Tracks.name
        FROM Links
        JOIN Tracks ON Links.track_id = Tracks.id
        JOIN Artists ON Tracks.artist_id = Artists.id
        WHERE Links.url = ?
    ''', (link,))
    result = cursor.fetchone()
    artist_name, era, track_name = result if result else ('unknown', 'unknown', 'unknown')

    output_path = f'{parent_dir}/{sanitize_path(artist_name)}/{sanitize_path(era)}'
    makedirs(output_path, exist_ok=True)

    match file_hoster:
        case 'pillowcase':
            download_pillowcase(link, output_path)
        case 'krakenfiles':
            download_krakenfiles(link, output_path)
        case 'pixeldrain':
            download_pixeldrain(link, output_path)
        case 'unrecognized domain':
            print("Unrecognized domain, skipping...")


def download_pillowcase(link: str, output_dir: str):
    file_id = link.rstrip('/').split('/')[-1]
    if 'pillows' in link:
        domain = 'pillows'
    elif 'pillowcase' in link:
        domain = 'pillowcase'
    else:
        print('Pillowcase: Unrecognized domain')
        return ''

    # get extension for file
    r = requests.get(f'https://{domain}.su/f/{file_id}')
    match = search(r'filename:"(.*?)"', r.text)
    if not match:
        file_name = None
        for ext in COMMON_EXTS:
            url = f'https://api.{domain}.su/api/download/{file_id}{ext}'
            r = requests.head(url)  # HEAD request, no download
            if r.status_code == 200:
                file_name = f'unknown{ext}'
                break
        if not file_name:
            raise Exception(f'Pillowcase: Could not determine filename for {file_id}')
    else:
        file_name = match.group(1)

    # download
    ext = splitext(file_name)[1]
    download_url = f'https://api.{domain}.su/api/download/{file_id}{ext}'
    r = requests.get(download_url, stream=True)
    r.raise_for_status()
    with open(f'{output_dir}/{file_name}', 'wb') as f:
        copyfileobj(r.raw, f)
    print(f'Downloaded: {file_name}')
    return file_name


def download_krakenfiles(link: str, output_dir: str):
    k = Kraken()
    k.download_file(link, output_dir)


def download_pixeldrain(link: str, output_dir: str):
    file_id = link.split('/')[-1]
    pixeldrain.Sync.download_file(file_id, output_dir) # can add custom filename


def sanitize_path(s):
    return re.sub(r'[<>:"/\\|?*]', '', s).strip()


if __name__ == '__main__':
    main()