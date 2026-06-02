CREATE TABLE IF NOT EXISTS Artists (
    id INTEGER PRIMARY KEY,
    name TEXT,
    sheet_id TEXT,
    last_synced TIMESTAMP,
    up_to_date BOOLEAN,
    working BOOLEAN,
    alternate BOOLEAN,
    best_of BOOLEAN
);

CREATE TABLE IF NOT EXISTS Tracks (
    id INTEGER PRIMARY KEY,
    artist_id INTEGER,
    era TEXT,
    name TEXT,
    notes TEXT,
    quality TEXT,
    portion TEXT,
    track_length TEXT,
    recording_date TIMESTAMP,
    leak_date TIMESTAMP,
    snapshot_date TIMESTAMP,
    FOREIGN KEY (artist_id) REFERENCES Artists(id)
);

CREATE TABLE IF NOT EXISTS Links (
    id INTEGER PRIMARY KEY,
    track_id INTEGER,
    url TEXT,
    works BOOLEAN,
    FOREIGN KEY (track_id) REFERENCES Tracks(id)
);

CREATE TABLE IF NOT EXISTS Contributors (
    id INTEGER PRIMARY KEY,
    artist_id INTEGER,
    contributor TEXT,
    FOREIGN KEY (artist_id) REFERENCES Artists(id)
);