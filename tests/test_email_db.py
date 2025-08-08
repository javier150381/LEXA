import os
import tempfile
from unittest import TestCase, mock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database as db


class EmailDbTests(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "db.sqlite")
        self.patch_db = mock.patch.object(db, "DB_PATH", self.db_path)
        self.patch_db.start()
        db.init_db()
        db.add_caso(None, "CasoTest", "")
        self.caso_id = db.get_casos()[0][0]

    def tearDown(self):
        self.patch_db.stop()
        os.unlink(self.db_path)
        os.rmdir(self.tmp_dir)
        root_db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "app.db"))
        try:
            os.remove(root_db)
        except FileNotFoundError:
            pass

    def test_add_and_get_email(self):
        db.add_email(self.caso_id, "me@example.com", "Hola", "2024-01-01", "Body", "Nombre")
        rows = db.get_emails_by_caso(self.caso_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Nombre")
        self.assertEqual(rows[0][2], "me@example.com")
        self.assertEqual(rows[0][3], "Hola")
        self.assertEqual(rows[0][5], "Body")

    def test_init_db_migrates_old_email_table(self):
        # Replace the emails table with an old schema lacking the "nombre" column
        conn = db.connect()
        cur = conn.cursor()
        cur.execute('DROP TABLE emails')
        cur.execute(
            'CREATE TABLE emails ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'caso_id INTEGER, '
            'remite TEXT, '
            'asunto TEXT, '
            'fecha TEXT, '
            'cuerpo TEXT, '
            'FOREIGN KEY(caso_id) REFERENCES casos(id) ON DELETE CASCADE)'
        )
        conn.commit()
        conn.close()

        db.init_db()

        conn = db.connect()
        cur = conn.cursor()
        cur.execute('PRAGMA table_info(emails)')
        cols = [r[1] for r in cur.fetchall()]
        conn.close()

        self.assertIn('nombre', cols)

