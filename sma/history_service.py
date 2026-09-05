import sqlite3
import time

from sma.state import state


class HistoryService:


    def __init__(self, dbfile="history.db"):

        self.dbfile = dbfile
        self.conn = None
        self.history_retention_days = 365
        self.cleanup_interval = 24 * 60 * 60
        self.last_cleanup = 0

    def start(self):

        self.conn = sqlite3.connect(
            self.dbfile,
            check_same_thread=False
        )

        self.create_tables()

        print("HistoryService started")

        while True:

            try:

                self.save_snapshot()

                if time.time() - self.last_cleanup >= self.cleanup_interval:
                    self.cleanup_old_history()
                    self.last_cleanup = time.time()

            except Exception as e:
                print(f"HistoryService error: {e}")

            time.sleep(5)


    def create_tables(self):

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS history (

                timestamp INTEGER NOT NULL,

                pv_power REAL,

                house_load REAL,

                grid_import REAL,
                grid_export REAL,

                grid_import_counter INTEGER,
                grid_export_counter INTEGER,

                tag3_counter INTEGER,
                tag4_counter INTEGER,
                tag9_counter INTEGER,
                tag10_counter INTEGER,

                phase1_import_counter INTEGER,
                phase2_import_counter INTEGER,
                phase3_import_counter INTEGER,

                phase1_export_counter INTEGER,
                phase2_export_counter INTEGER,
                phase3_export_counter INTEGER,

                pv_day_yield REAL,
                pv_total_yield REAL

            )
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_timestamp
            ON history(timestamp)
        """)

        self.conn.commit()

    def save_snapshot(self):

        data = state.get()
        summary = data.get("summary", {})
        energy = data.get("energy_meter", {})

        self.conn.execute(
            """
            INSERT INTO history (

                timestamp,

                pv_power,
                house_load,

                grid_import,
                grid_export,

                grid_import_counter,
                grid_export_counter,

                tag3_counter,
                tag4_counter,
                tag9_counter,
                tag10_counter,

                phase1_import_counter,
                phase2_import_counter,
                phase3_import_counter,

                phase1_export_counter,
                phase2_export_counter,
                phase3_export_counter,

                pv_day_yield,
                pv_total_yield

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(time.time()),

                summary.get("pv_power", 0),
                summary.get("house_load", 0),

                summary.get("grid_import", 0),
                summary.get("grid_export", 0),

                energy.get("grid_import_counter", 0),
                energy.get("grid_export_counter", 0),

                energy.get("tag3_counter", 0),
                energy.get("tag4_counter", 0),
                energy.get("tag9_counter", 0),
                energy.get("tag10_counter", 0),

                energy.get("phase1_import_counter", 0),
                energy.get("phase2_import_counter", 0),
                energy.get("phase3_import_counter", 0),

                energy.get("phase1_export_counter", 0),
                energy.get("phase2_export_counter", 0),
                energy.get("phase3_export_counter", 0),


                summary.get("pv_day_yield", 0),
                summary.get("pv_total_yield", 0),
            )
        )

        self.conn.commit()

    def cleanup_old_history(self):
        cutoff = int(time.time()) - (self.history_retention_days * 24 * 60 * 60)

        cursor = self.conn.execute(
            "DELETE FROM history WHERE timestamp < ?",
            (cutoff,)
        )
        self.conn.commit()

        if cursor.rowcount > 0:
            print(
                f"HistoryService cleanup: removed {cursor.rowcount} "
                f"rows older than {self.history_retention_days} days"
            )

    def get_history(self, limit=100):

        cursor = self.conn.execute(
            """
            SELECT
                timestamp,
                pv_power,
                house_load,
                grid_import,
                grid_export,
                grid_import_counter,
                grid_export_counter,
                pv_day_yield,
                pv_total_yield
            FROM history
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = list(reversed(cursor.fetchall()))

        MAX_POINTS = 1000

        if len(rows) > MAX_POINTS:
            step = max(1, len(rows) // MAX_POINTS)
            rows = rows[::step]

        return [
            {
                "timestamp": row[0],
                "pv_power": row[1],
                "house_load": row[2],
                "grid_import": row[3],
                "grid_export": row[4],
                "grid_import_counter": row[5],
                "grid_export_counter": row[6],
                "pv_day_yield": row[7],
                "pv_total_yield": row[8],
            }
            for row in rows
        ]
    def get_today_energy(self):

         now = int(time.time())

         local = time.localtime(now)

         midnight = int(
             time.mktime(
                 (
                     local.tm_year,
                     local.tm_mon,
                     local.tm_mday,
                     0, 0, 0,
                     local.tm_wday,
                     local.tm_yday,
                     local.tm_isdst
                 )
             )
         )


         first = self.conn.execute(
             """
             SELECT
                  grid_import_counter,
                  grid_export_counter
             FROM history
             WHERE
                 timestamp >= ?
                 AND (
                     grid_import_counter > 0
                     OR grid_export_counter > 0
                 )
             ORDER BY timestamp ASC
             LIMIT 1
             """,
             (midnight,)
         ).fetchone()


         last = self.conn.execute(
             """
             SELECT
                 grid_import_counter,
                 grid_export_counter,
                 pv_day_yield
             FROM history
             WHERE timestamp >= ?
             ORDER BY timestamp DESC
             LIMIT 1
             """,
             (midnight,)
         ).fetchone()


         if not first or not last:
             return {}


         grid_import = (last[0] - first[0]) / 3_600_000
         grid_export = (last[1] - first[1]) / 3_600_000

         pv = last[2]

         house = pv + grid_import - grid_export

         if house > 0:
             self_sufficiency = (
                 (pv - grid_export) / house
             ) * 100
         else:
             self_sufficiency = 0

         return {

             "pv_day_yield": round(pv, 2),

             "grid_import": round(grid_import, 2),

             "grid_export": round(grid_export, 2),

             "house_load": round(house, 2),

             "self_sufficiency": round(self_sufficiency, 1)

         }
