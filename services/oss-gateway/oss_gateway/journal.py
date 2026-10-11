"""Durable upload intents and delete outbox; never persist service API keys."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import uuid


class Journal:
    def __init__(self, path):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS images (
                    namespace TEXT NOT NULL, image_id TEXT NOT NULL,
                    object_key TEXT NOT NULL, PRIMARY KEY (namespace, image_id));
                CREATE TABLE IF NOT EXISTS uploads (
                    id TEXT PRIMARY KEY, namespace TEXT NOT NULL, subject TEXT NOT NULL,
                    previous_ids TEXT NOT NULL, object_key TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS deletes (
                    id TEXT PRIMARY KEY, namespace TEXT NOT NULL, images TEXT NOT NULL,
                    ready INTEGER NOT NULL DEFAULT 0);
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA synchronous=FULL')
            with db:
                yield db
        finally:
            db.close()

    def check(self):
        with self.connection() as db:
            db.execute('SELECT 1').fetchone()

    def image(self, namespace, image_id):
        with self.connection() as db:
            row = db.execute('SELECT object_key FROM images WHERE namespace=? AND image_id=?',
                             (namespace,image_id)).fetchone()
            return row['object_key'] if row else None

    def begin_upload(self, namespace, subject, previous_ids, object_key):
        operation = uuid.uuid4().hex
        with self.connection() as db:
            db.execute('INSERT INTO uploads VALUES (?,?,?,?,?)',
                       (operation,namespace,subject,json.dumps(previous_ids),object_key))
        return operation

    def complete_upload(self, operation, image_id):
        with self.connection() as db:
            row = db.execute('SELECT * FROM uploads WHERE id=?', (operation,)).fetchone()
            db.execute('INSERT INTO images VALUES (?,?,?)', (row['namespace'],image_id,row['object_key']))
            db.execute('DELETE FROM uploads WHERE id=?', (operation,))

    def uploads(self, namespace):
        with self.connection() as db:
            return [dict(row) for row in db.execute('SELECT * FROM uploads WHERE namespace=?', (namespace,))]

    def discard_upload(self, operation):
        with self.connection() as db:
            row = db.execute('SELECT * FROM uploads WHERE id=?', (operation,)).fetchone()
            db.execute('INSERT INTO deletes VALUES (?,?,?,1)',
                       (uuid.uuid4().hex,row['namespace'],json.dumps([{'image_id':None,'object_key':row['object_key']}])))
            db.execute('DELETE FROM uploads WHERE id=?', (operation,))

    def plan_delete(self, namespace, image_ids):
        operation = uuid.uuid4().hex
        with self.connection() as db:
            images = []
            for image_id in image_ids:
                row = db.execute('SELECT object_key FROM images WHERE namespace=? AND image_id=?',
                                 (namespace,image_id)).fetchone()
                # Track backend targets even when a legacy DB image has not yet
                # been migrated; a timed-out delete can still commit later.
                images.append({'image_id':image_id,'object_key':row['object_key'] if row else None})
            db.execute('INSERT INTO deletes VALUES (?,?,?,0)', (operation,namespace,json.dumps(images)))
        return operation

    def finish_delete(self, operation, deleted_ids=None):
        with self.connection() as db:
            row = db.execute('SELECT * FROM deletes WHERE id=?', (operation,)).fetchone()
            images = json.loads(row['images'])
            if deleted_ids is not None:
                images = [image for image in images if image['image_id'] in deleted_ids]
            for image in images:
                db.execute('DELETE FROM images WHERE namespace=? AND image_id=?',
                           (row['namespace'],image['image_id']))
            db.execute('UPDATE deletes SET images=?, ready=1 WHERE id=?', (json.dumps(images),operation))

    def discard_delete(self, operation):
        with self.connection() as db:
            db.execute('DELETE FROM deletes WHERE id=?', (operation,))

    def prepared_deletes(self, namespace):
        with self.connection() as db:
            return [dict(row) for row in db.execute('SELECT * FROM deletes WHERE namespace=? AND ready=0', (namespace,))]

    def pending_deletes(self, namespace):
        with self.connection() as db:
            return db.execute('SELECT count(*) FROM deletes WHERE namespace=?', (namespace,)).fetchone()[0]

    def flush(self, store):
        with self.connection() as db:
            rows = list(db.execute('SELECT * FROM deletes WHERE ready=1 LIMIT 50'))
        for row in rows:
            for image in json.loads(row['images']):
                if image['object_key'] is not None:
                    store.delete(image['object_key'])
            with self.connection() as db:
                db.execute('DELETE FROM deletes WHERE id=?', (row['id'],))
