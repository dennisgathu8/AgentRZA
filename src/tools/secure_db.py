import duckdb
import json
from config.settings import get_settings
from cryptography.fernet import Fernet
import os
from contextlib import contextmanager

settings = get_settings()

class SecureDB:
    """
    DuckDB instance managed via Fernet encryption at rest.
    Data is written to encrypted parquet files rather than open duckdb format.
    """
    def __init__(self):
        # We use an in-memory DuckDB for processing...
        self.conn = duckdb.connect(':memory:')
        self.fernet = Fernet(settings.get_fernet_bytes())
        self.db_path = settings.duckdb_path
        self._init_schema()
        
    def _init_schema(self):
        # Create staging tables for the Enriched Match and Events
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id BIGINT PRIMARY KEY,
                home_team VARCHAR,
                away_team VARCHAR,
                total_home_xg DOUBLE,
                total_away_xg DOUBLE,
                status VARCHAR,
                tracking_frames JSON
            );
            
            CREATE TABLE IF NOT EXISTS events (
                event_id VARCHAR PRIMARY KEY,
                match_id BIGINT,
                index INT,
                period INT,
                minute INT,
                second INT,
                type_name VARCHAR,
                player_name VARCHAR,
                xg DOUBLE,
                xa DOUBLE
            );
        """)

    def upsert_match_data(self, payload: dict):
        """
        Take a MatchEnrichedPayload dict and upsert it into the DuckDB relations.
        Using execute for parameterized queries to prevent SQL injection.
        """
        match = payload['match']
        events = payload['events']
        
        # Upsert match (Insert OR Replace semantics)
        self.conn.execute("""
            INSERT OR REPLACE INTO matches 
            (match_id, home_team, away_team, total_home_xg, total_away_xg, status, tracking_frames)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            match['match_id'], 
            match['home_team']['team_name'], 
            match['away_team']['team_name'],
            payload['total_home_xg'],
            payload['total_away_xg'],
            match['status'],
            json.dumps(payload.get('tracking_frames', []))
        ))
        
        # Batch insert events
        for e in events:
            xg = e.get('shot_context', {}).get('xg') if e.get('shot_context') else None
            xa = e.get('shot_context', {}).get('xa') if e.get('shot_context') else None
            player_name = e.get('player', {}).get('player_name') if e.get('player') else None
            
            self.conn.execute("""
                INSERT OR REPLACE INTO events 
                (event_id, match_id, index, period, minute, second, type_name, player_name, xg, xa)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                e['event_id'],
                e['match_id'],
                e['index'],
                e['period'],
                e['minute'],
                e['second'],
                e['type_name'],
                player_name,
                xg,
                xa
            ))

    def flush_to_encrypted_disk(self):
        """
        Dump tables to parquet, read as bytes, encrypt via Fernet, and save to disk.
        Ensures Zero-Trust At-Rest encryption.
        """
        temp_matches = "data/raw/matches_temp.parquet"
        temp_events = "data/raw/events_temp.parquet"
        
        self.conn.execute(f"COPY matches TO '{temp_matches}' (FORMAT PARQUET)")
        self.conn.execute(f"COPY events TO '{temp_events}' (FORMAT PARQUET)")
        
        # Encrypt the parquet payload
        def encrypt_file(source, dest):
            if os.path.exists(source):
                with open(source, 'rb') as f:
                    data = f.read()
                encrypted = self.fernet.encrypt(data)
                with open(dest, 'wb') as f:
                    f.write(encrypted)
                os.remove(source) # Secure wipe should be used in true PROD, standard remove here
        
        encrypt_file(temp_matches, settings.duckdb_path.replace('.duckdb', '_matches.enc'))
        encrypt_file(temp_events, settings.duckdb_path.replace('.duckdb', '_events.enc'))
        
    def close(self):
        self.conn.close()

@contextmanager
def secure_db_session():
    db = SecureDB()
    try:
        yield db
    finally:
        db.close()
