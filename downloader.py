
from asyncio import sleep
from concurrent.futures import ThreadPoolExecutor
from re import search
from requests import get
from os import remove, makedirs
from os.path import exists, join, isfile
from shutil import copyfileobj, rmtree

INPUT_FILE = "input.txt"
OUTPUT_DIR = "output"

PAGE_URL = "https://pillowcase.su/f/"
API_URL = "https://api.pillowcase.su/api/download/"

FILE_NAME_REGEX = r'filename:"(.*?)",cover:'

THREAD_POOL_SIZE = 32

thread_pool = ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE)

def fetch_file_info(file_id):
    print(f"Fetching file info for ID: {file_id}")
    url = f"{PAGE_URL}{file_id}"
    response = get(url)
    if response.status_code == 200:
        match = search(FILE_NAME_REGEX, response.text)
        if match:
            file_name = match.group(1)
            return file_name
        else:
            raise Exception("Filename not found in the response")
    else:
        raise Exception(f"Failed to fetch file info: {response.status_code}")

def download_file(file_id, file_name):
    print(f"Downloading: {file_name}")
    url = f"{API_URL}{file_id}"
    response = get(url, stream=True)
    if response.status_code == 200:
        with open(join(OUTPUT_DIR, file_name), "wb") as file:
            copyfileobj(response.raw, file)
        print(f"Downloaded: {file_name}")
    else:
        if response.status_code == 408:
            print(f"Request timed out downloading {file_name}. Retrying in 5 seconds...")
            sleep(5)
            download_file(file_id, file_name)
        else:
            print(f"Failed to download {file_name}: {response.status_code}")
            raise Exception(f"Failed to download file: {response.status_code}")

# Prepare the output directory
if exists(OUTPUT_DIR) and isfile(OUTPUT_DIR):
    remove(OUTPUT_DIR)
elif exists(OUTPUT_DIR):
    rmtree(OUTPUT_DIR)
makedirs(OUTPUT_DIR)

# Read the input file and extract links
links = []
with open(INPUT_FILE, "r") as file:
    for line in file.readlines():
        line = line.strip()
        if "pillows.su" in line:
            file_id = line.split("/")[-1]
            links.append(file_id)
        else:
            print(f"Invalid link: {line.strip()}")

# Process the links in parallel
def process_link(link):
    try:
        file_name = fetch_file_info(link)
        download_file(link, file_name)
    except Exception as e:
        print(f"Error processing {link}: {e}")

for link in links:
    try:
        thread_pool.submit(process_link, link)
    except Exception as e:
        print(f"Error processing {link}: {e}")
