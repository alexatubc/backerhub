from constants import *
from emoji import replace_emoji
import requests
import sqlite3




# sheet id retrieved from gui.py
SHEET_ID = '1Z8aANbxXbnUGoZPRvJfWL3gz6jrzPPrwVt3d0c1iJ_4'


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
        artist_id = artist[0]
        sheet_id = artist[2]
        artist_sheet = call_sheet(sheet_id, 'unreleased')
        if not artist_sheet:
            # this currently can't account for not accessing due to network issues (not a dead sheet)
            print(f'Couldn\'t access {artist[1]}\'s tracker.')
            cursor.execute('UPDATE Artists SET working = ? WHERE id = ?', ('No', artist[0]))
            connection.commit()
            continue
        # trackers are unstandardized, this builds a map for where each column is dynamically
        header = artist_sheet[0].get('values', '')
        col_map = build_col_map(header)
        for row in artist_sheet:
            try:
                # doesn't scrape rows containing headers, footers, and era info pages
                # TODO: doesn't pick up headers (e.g. 50 cent tracker)
                if not is_song(row, col_map):
                    continue
                track_tuple = get_track_tuple(artist, row, col_map)
                cursor.execute(insertTrackQuery, track_tuple)
                cursor.execute(
                    'SELECT id FROM Tracks WHERE artist_id = ? AND name = ?',
                    (artist_id, track_tuple[2])  # artist_id, name
                )
                track_id = cursor.fetchone()[0]
                link_tuple = get_link_tuple(row, track_id, col_map)
                if not all(link_tuple):
                    connection.commit()
                    continue
                cursor.execute(insertLinkQuery, link_tuple)
                connection.commit()
            except (IndexError, KeyError) as e:
                print(f'{e}')
        print(f'Accessed {artist[1]}\'s sheet. {num_artists_accessed}/{num_artists_total} sheets accessed.')
        num_artists_accessed += 1


def call_sheet(sheet_id: str, tab_keyword: str = '') -> list:
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}'
    if tab_keyword:
        sheet_meta_data = requests.get(url).json().get('sheets', [])
        sheet_name_list = [s['properties']['title'].lower() for s in sheet_meta_data]
        if len(sheet_name_list) > 1:
            sheet_name = next((sheet for sheet in sheet_name_list if tab_keyword in sheet), None)
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
        worksheet = workbook[0]['data'][0].get('rowData', [])stuff
        return worksheet
    # TODO: change to raise errorstuff
    # TODO: Describe specific error
    except IndexError as e:
        return []
    except requests.exceptions.HTTPError as e:
        print("HTTP error occurred:", e)
        return []
    except requests.exceptions.RequestException as e:
        print("Request error occurred:", e)
        return []


def get_cell(row, index: int, string_format: str='formattedValue', default: str='') -> str:
    if index is None:
        return default
    try:
        cell = row['values'][index]
        text = cell.get(string_format, default).strip()

        # urls can be stored differently depending on how it was linked, which illicits this back up option
        if string_format == 'hyperlink' and text == '':
            for run in cell.get('textFormatRuns', []):
                uri = run.get('format', {}).get('link', {}).get('uri')
                if uri:
                    return uri
        return text
    except (IndexError, KeyError):
        return default


def sanitize_name(name: str) -> str:
    try:
        # unsure if name_no_tags is required, as it makes identifying artist sheets of the same artist hard in sqlite
        name_no_tags = name.split('[')[0] # this may be causing issues
        name_no_emoji = replace_emoji(name_no_tags, replace='').strip()
        return name_no_emoji
    except (AttributeError, IndexError):
        # TODO: change to raise error
        return ''


def find_sheet_id(url: str) -> str:
    if not url:
        return ''
    sheet_id = url.split('/d/')[1].split('/')[0]
    return sheet_id


def is_tracker_alternate(name: str) -> str:
    if "alt" in name.lower():
        return 'Yes'
    else:
        return 'No'


def is_tracker_bestof(name: str) -> str:
    if "⭐️" in name or "⭐" in name:
        return 'Yes'
    else:
        return 'No'


def get_artist_tuple(row: list[str]) -> tuple:
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


def is_song(row: list[str], col_map: dict) -> bool:
    name = get_cell(row, col_map['name']).lower()
    era = get_cell(row, col_map['era']).lower()
    quality = get_cell(row, col_map['quality']).lower()
    portion = get_cell(row, col_map['portion']).lower()

    if any(v in HEADER_VALUES for v in [name, era, quality, portion]):
        return False
    if name and not quality and not portion:
        return False
    if not name:
        return False

    return True


def get_track_tuple(artist: list[str], row: list[str], col_map: dict) -> tuple:
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


def get_link_tuple(row: list[str], track_id: str, col_map: dict) -> tuple:
    track_id = track_id
    link = get_cell(row, col_map['links'], 'hyperlink')
    works = 'Yes'  # needs to check through requests maybe? or if its pillows do an api req?

    link_tuple = (track_id, link, works)
    return link_tuple


def build_col_map(header: list) -> dict:
    # some headers are on line 2
    col_map = {}
    for idx, col_value in enumerate(header):
        # TODO: make this more readable
        col_name = ' '.join(col_value.get('formattedValue', '').replace('\n', ' ').split())
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
    # puts none if the column type wasnt detected. this is easier than dealing with the error at function get_cell
    for col in COLUMN_KEYWORDS.keys():
        if col not in col_map.keys():
            col_map[col] = None

    return col_map


if __name__ == '__main__':
    main()

# test
