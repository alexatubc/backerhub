import datetime
from dotenv import load_dotenv
import os

COLUMN_KEYWORDS = {
    'era': ['era', 'year'],
    'name': ['name', 'title'],
    'notes': ['notes', 'note'],
    'track length': ['track', 'duration'],
    'record date': ['file date', 'record date', 'recording date', 'recorded date', 'origin date'],
    'leak date': ['leak date', 'leaked date'],
    'quality': ['quality'],
    'portion': ['portion', 'available', 'type'],
    'links': ['link', 'link(s)', 'download', 'downloads', 'source', 'source(s)', 'download/link(s)'],
}

MERGED_COL_KEYWORDS = {
    'portion/quality': ['what\'s available', 'what\'s new?']
}

insertArtistQuery = '''
    INSERT OR IGNORE INTO 
    Artists (name, sheet_id, last_synced, up_to_date, working, alternate, best_of) 
    VALUES (?, ?, ?, ?, ?, ?, ?);
'''
insertTrackQuery = '''
    INSERT OR IGNORE INTO
    Tracks (artist_id, era, name, notes, quality, portion, track_length, recording_date, leak_date, snapshot_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
'''
insertLinkQuery = '''
    INSERT OR IGNORE INTO
    Links (track_id, url, works)
    VALUES (?, ?, ?)
'''  # could try to recogize what the link leads to (e.g. image-sharing, video-sharing, news, etc.)

load_dotenv()
API_KEY = os.getenv('GOOGLE_API_KEY')

CURRENTDATETIME = datetime.datetime.now()
