from dotenv import load_dotenv
import os
import requests
import sqlite3
import datetime
from emoji import replace_emoji


load_dotenv()
API_KEY = os.getenv('GOOGLE_API_KEY')

# sheet id retrieved from gui.py
SHEET_ID = '1Z8aANbxXbnUGoZPRvJfWL3gz6jrzPPrwVt3d0c1iJ_4'

CURRENTDATETIME = datetime.datetime.now()

GRIMMR3XX_TEMPLATE = ['era', 'name', 'notes', 'track length', 'file date', 'leak date', 'type', 'portion', 'quality', 'link(s)']

COLUMN_KEYWORDS = {
    'era' : ['era', 'year'],
    'name' : ['name', 'title'],
    'notes' : ['notes', 'note'],
    'track length' : ['track', 'duration'],
    'record date' : ['file date', 'record date', 'recording date', 'recorded date', 'origin date'],
    'leak date' : ['leak date', 'leaked date'],
    'quality' : ['quality'],
    'portion' : ['portion', 'available', 'type'],
    'links' : ['link', 'link(s)', 'download', 'downloads', 'source', 'source(s)', 'download/link(s)'],
}

MERGED_COL_KEYWORDS = {
    'portion/quality' : ['what\'s available','what\'s new?']
}

insertArtistQuery = '''
    INSERT INTO 
    Artists (name, sheet_id, last_synced, up_to_date, working, alternate, best_of) 
    VALUES (?, ?, ?, ?, ?, ?, ?);
'''
insertTrackQuery = '''
    INSERT INTO
    Tracks (artist_id, era, name, notes, quality, portion, track_length, recording_date, leak_date, snapshot_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
'''
insertLinkQuery = '''
    INSERT INTO
    Links (track_id, url, works)
    VALUES (?, ?, ?)
''' # could try to recogize what the link leads to (e.g. image-sharing, video-sharing, news, etc.)


def main():

    connection = sqlite3.connect('TrackerHub.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cursor = connection.cursor()
    with open('schema.sql', 'r') as schema:
        cursor.executescript(schema.read())

    main_sheet = call_sheet(SHEET_ID)
    if not main_sheet:
        raise Exception("Cannot access main sheet...")

    # scrapes info about artist google sheets (name, url, etc.)
    for row in main_sheet:
        try:
            artist_tuple = get_artist_tuple(row)
            if not all(artist_tuple):
                continue
            cursor.execute(insertArtistQuery, artist_tuple)
            connection.commit()
        except (IndexError, KeyError) as e:
            print(f'{e}')

    # scrapes track info from artist google sheets (name, quality, portion, etc.)
    cursor.execute('SELECT * FROM Artists')
    trackersheet = cursor.fetchall()

    num_artists_total = len(trackersheet)
    num_artists_accessed = 1
    for artist in trackersheet:
        sheet_id = artist[2]
        artist_sheet = call_sheet(sheet_id, 'unreleased')
        if not artist_sheet:
            print(f'Couldn\'t access {artist[0]}\'s sheet')
            continue
        # artist trackers are unstandardized, meaning its currently too hard to scrape all of them
        # this function will check if it follows the GrimmR3xx or Ye template, but can be expanded later
        header = artist_sheet[0].get('values', '')
        if not follows_tracker_template(header, GRIMMR3XX_TEMPLATE):
            print(f'{artist[1]}\'s sheet does not have a recognized template')
            pass
        col_map = build_col_map(header)
        print(col_map)
        for row in artist_sheet:
            try:
                # doesn't scrape rows containing headers, footers, and era info pages
                # TODO: doesn't pick up headers (e.g. 50 cent tracker)
                if not is_song(row):
                    continue
                track_tuple = get_track_tuple(artist, row, col_map)
                cursor.execute(insertTrackQuery, track_tuple)
                link_tuple = get_link_tuple(row, cursor.lastrowid, col_map)
                if not all(link_tuple):
                    connection.commit()
                    continue
                cursor.execute(insertLinkQuery, link_tuple)
                connection.commit()
            except (IndexError, KeyError) as e:
                print(f'{e}')
        print(f'Accessed {artist[1]}\'s sheet. {num_artists_accessed}/{num_artists_total} sheets accessed.')
        num_artists_accessed += 1

def call_sheet(sheet_id, keyword=''):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}'
    if keyword:
        meta = requests.get(url).json().get('sheets', [])
        sheet_name_list = [s['properties']['title'].lower() for s in meta]
        if len(sheet_name_list) > 1:
            sheet_name = next((sheet for sheet in sheet_name_list if keyword in sheet), None)
        else:
            # returns first sheet because function is currently expected to use 'unreleased' as its keyword
            # this logic should be changed if the project scope is expanded outside the unreleased sheet
            sheet_name = ''
    else:
        sheet_name = ''
    params = {
        'includeGridData': 'true',
        'ranges': f'{sheet_name}!A1:Z1000',
        'key': API_KEY
    }
    response = requests.get(url, params=params)

    try:
        response.raise_for_status()
        workbook = response.json().get('sheets', [])
        worksheet = workbook[0]['data'][0].get('rowData', [])
        return worksheet
    # TODO: change to raise error
    except IndexError as e:
        return []
    except requests.exceptions.HTTPError as e:
        print("HTTP error occurred:", e)
    except requests.exceptions.RequestException as e:
        print("Request error occurred:", e)

def get_cell(row, index, string_format='formattedValue', default=''):
    if index is None:
        return default
    try:
        cell = row['values'][index]
        text = cell.get(string_format, default).strip()

        # urls can be stored differently depending on how it was linked, which illicits this back up
        if string_format == 'hyperlink' and text == '':
            for run in cell.get('textFormatRuns', []):
                uri = run.get('format', {}).get('link', {}).get('uri')
                if uri:
                    return uri
        return text
    except (IndexError, KeyError):
        return default

def sanitize_name(name):
    try:
        name_no_tags = name.split('[')[0]
        name_no_emoji = replace_emoji(name_no_tags, replace='').strip()
        return name_no_emoji
    except (AttributeError, IndexError):
        # TODO: change to raise error
        return ''

def find_sheet_id(url):
    if not url:
        return ''
    sheet_id = url.split('/d/')[1].split('/')[0]
    return sheet_id

def is_tracker_alternate(name):
    if "alt" in name.lower():
        return 'Yes'
    else:
        return 'No'

def is_tracker_bestof(name):
    if "⭐️" in name or "⭐" in name:
        return 'Yes'
    else:
        return 'No'

def get_artist_tuple(row):
    artist_name = sanitize_name(get_cell(row, 0))
    sheet_id = find_sheet_id(get_cell(row, 0, 'hyperlink'))
    alternate = is_tracker_alternate(get_cell(row, 0))
    best_of = is_tracker_bestof(get_cell(row, 0))
    credits = get_cell(row, 1)  # currently unreferenced
    up_to_date = get_cell(row, 2)
    working = get_cell(row, 3)
    last_synced = CURRENTDATETIME

    if sheet_id == 'e':
        working = 'No'
    artist_tuple = (artist_name, sheet_id, last_synced, up_to_date, working, alternate, best_of)
    return artist_tuple

def follows_tracker_template(header, keywords):
    # TODO: fix
    for idx, cell in enumerate(header):
        if cell.get('formattedValue','').lower() != keywords[idx]:
            return False
    return True

def is_song(row):
    # TODO: compact/pythonicize
    if get_cell(row, 0) == '':
        return False
    elif get_cell(row, 1) == '':
        return False
    elif get_cell(row, 7) == '':
        return False
    elif get_cell(row, 8) == '':
        return False
    else:
        return True

def get_track_tuple(artist, row, col_map):
    artist_id = artist[0]
    era = get_cell(row, col_map['era'])
    name = get_cell(row, col_map['name'])
    notes = get_cell(row, col_map['notes'])
    track_length = get_cell(row, col_map['track length'])
    file_date = get_cell(row, col_map['record date'])
    leak_date = get_cell(row, col_map['leak date'])
    portion = get_cell(row, col_map['portion'])
    quality = get_cell(row, col_map['quality'])
    last_synced = CURRENTDATETIME

    track_tuple = (artist_id, era, name, notes, quality, portion, track_length, file_date, leak_date, last_synced)
    return track_tuple

def get_link_tuple(row, track_id, col_map):
    track_id = track_id
    link = get_cell(row, col_map['links'], 'hyperlink')
    works = 'Yes' # needs to check through requests maybe? or if its pillows do an api req?

    link_tuple = (track_id, link, works)
    return link_tuple

def build_col_map(header):
    col_map = {}
    for idx, col_value in enumerate(header):
        # TODO: make this more readable
        col_name = ' '.join(col_value.get('formattedValue','').replace('\n',' ').split())
        # some trackers concetrate information into one column (see travis scott sheet, "What's New?")
        # this loop will detect this
        for key, value in MERGED_COL_KEYWORDS.items():
            col_name_list = key.split('/')
            # checking if column name in dictionary because the other way around would require accounting for
            # all instances that exist (including symbols) which requires a bigger COLUMN_KEYWORDS dict
            if any(keyword in col_name.lower() for keyword in value):
                for col in col_name_list:
                    col_map[col] = idx
        for key, value in COLUMN_KEYWORDS.items():
            if any(keyword in col_name.lower() for keyword in value):
                col_map[key] = idx
                break
    for col in COLUMN_KEYWORDS.keys():
        if col not in col_map.keys():
            col_map[col] = None

    return col_map

if __name__ == '__main__':
    main()

# test
