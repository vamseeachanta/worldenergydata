"""Tests for wellpath data models (dataclasses and non-DB methods)."""

import os
import sqlite3

from worldenergydata.common.legacy.wellpath_models import (
    BASE_EXT,
    NewWell,
    StratigraphyMarker,
    SurveyData,
    Well,
    WellMap,
    WellSurface,
)


class TestBASEEXT:
    def test_value(self):
        assert BASE_EXT == ".db"


class TestWellSurface:
    def test_fields(self):
        ws = WellSurface(
            name="Well A",
            latitude=29.5,
            longitude=-93.8,
            altitude=10.0,
        )
        assert ws.name == "Well A"
        assert ws.latitude == 29.5
        assert ws.longitude == -93.8
        assert ws.altitude == 10.0


class TestSurveyData:
    def test_defaults(self):
        sd = SurveyData()
        assert sd.depth == 0.0
        assert sd.inc == 0.0
        assert sd.azi == 0.0
        assert sd.tvd == 0.0
        assert sd.north == 0.0
        assert sd.east == 0.0
        assert sd.closure == 0.0
        assert sd.dls == 0.0

    def test_custom(self):
        sd = SurveyData(depth=1000, inc=15.0, azi=120.0, tvd=985.0)
        assert sd.depth == 1000
        assert sd.inc == 15.0
        assert sd.azi == 120.0
        assert sd.tvd == 985.0


class TestStratigraphyMarker:
    def test_required_fields(self):
        sm = StratigraphyMarker(depth=5000, name="Miocene", color="#aabbcc")
        assert sm.depth == 5000
        assert sm.name == "Miocene"
        assert sm.color == "#aabbcc"

    def test_defaults(self):
        sm = StratigraphyMarker(depth=0, name="X", color="red")
        assert sm.tvd == 0.0
        assert sm.inc == 0.0
        assert sm.azi == 0.0
        assert sm.north == 0.0
        assert sm.east == 0.0
        assert sm.altitude == 0.0
        assert sm.latitude == 0.0
        assert sm.longitude == 0.0


class TestWellStr:
    def test_str(self):
        w = Well("WellA", 5000.0, 15.0, 120.0)
        s = str(w)
        assert "WellA" in s
        assert "5000.0" in s
        assert "15.0" in s
        assert "120.0" in s

    def test_initial_lists(self):
        w = Well("W", 0, 0, 0)
        assert w.depthlist == []
        assert w.inclist == []
        assert w.azilist == []


class TestWellMapStr:
    def test_str(self):
        wm = WellMap("WellB", 3000.0, 29.5, -93.8)
        s = str(wm)
        assert "WellB" in s
        assert "3000.0" in s
        assert "29.5" in s

    def test_getName(self):
        wm = WellMap("WellC", 0, 0, 0)
        assert wm.getName() == "WellC"

    def test_initial_lists(self):
        wm = WellMap("W", 0, 0, 0)
        assert wm.tvdlist == []
        assert wm.latlist == []
        assert wm.lonlist == []
        assert wm.strat_altilist == []
        assert wm.strat_latlist == []
        assert wm.strat_lonlist == []
        assert wm.strat_colorlist == []


class TestNewWellInit:
    def test_attributes(self):
        nw = NewWell("TestWell", 29.5, -93.8, 10.0)
        assert nw.newname == "TestWell"
        assert nw.latitude == 29.5
        assert nw.longitude == -93.8
        assert nw.altitude == 10.0


class TestNewWellCreate:
    def _setup_wellnames_db(self, tmp_path):
        """Create the wellnames.db with a wells table."""
        conn = sqlite3.connect(str(tmp_path / "wellnames.db"))
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE wells(name TEXT, latitude REAL, longitude REAL, altitude REAL)"
        )
        conn.commit()
        conn.close()

    def test_create_new_well_db(self, tmp_path):
        """Test creating a new well database with all tables."""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            self._setup_wellnames_db(tmp_path)
            nw = NewWell("TestWell1", 29.5, -93.8, 10.0)
            nw.create()
            db_path = tmp_path / "TestWell1.db"
            assert db_path.exists()

            # Verify geosurvey table exists with initial row
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM geosurvey")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 0  # Depth = 0

            # Verify stratigraphy table
            cursor.execute("SELECT * FROM stratigraphy")
            strat_rows = cursor.fetchall()
            assert len(strat_rows) == 1
            assert strat_rows[0][1] == "Holocene"
            assert strat_rows[0][8] == 10.0  # Fm_alt = altitude
            assert strat_rows[0][9] == 29.5  # Fm_lat = latitude
            assert strat_rows[0][10] == -93.8  # Fm_lon = longitude

            # Verify wellmap table
            cursor.execute("SELECT * FROM wellmap")
            map_rows = cursor.fetchall()
            assert len(map_rows) == 1
            assert map_rows[0][0] == 10.0  # altitude
            assert map_rows[0][1] == 29.5  # latitude
            assert map_rows[0][2] == -93.8  # longitude
            conn.close()
        finally:
            os.chdir(original_dir)

    def test_create_duplicate_name_adds_suffix(self, tmp_path):
        """Test that duplicate names get a '2' suffix."""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            nw = NewWell("Existing", 0, 0, 0)
            nw.create(wellnames_given=["Existing"])
            assert nw.newname == "Existing2"
        finally:
            os.chdir(original_dir)

    def test_create_dot_in_name_replaced(self, tmp_path):
        """Test that dots in well names are replaced with *."""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            self._setup_wellnames_db(tmp_path)
            nw = NewWell("Well.1", 0, 0, 0)
            nw.create()
            # The DB filename uses tryname which has * instead of .
            db_path = tmp_path / "Well*1.db"
            assert db_path.exists()
        finally:
            os.chdir(original_dir)

    def test_create_apostrophe_stripped(self, tmp_path):
        """Test that apostrophes are stripped for name comparison."""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            nw = NewWell("O'Brien", 0, 0, 0)
            nw.create(wellnames_given=["OBrien"])
            # tryname = "OBrien" which is in wellnames_given, so name gets "2" suffix
            assert nw.newname == "O'Brien2"
        finally:
            os.chdir(original_dir)


class TestWellDbMethods:
    def _create_test_db(self, tmp_path, well_name):
        """Helper to create a test well database."""
        db_path = tmp_path / (well_name + ".db")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE geosurvey("
            "Depth REAL PRIMARY KEY, Inc REAL, Azi REAL,"
            "TVD REAL, North REAL, East REAL, Closure, DLS)"
        )
        cursor.execute("INSERT INTO geosurvey VALUES(0, 0, 0, 0, 0, 0, 0, 0)")
        cursor.execute(
            "INSERT INTO geosurvey VALUES(100, 2.5, 45.0, 99.9, 1.0, 0.5, 0, 0)"
        )
        cursor.execute(
            "INSERT INTO geosurvey VALUES(200, 5.0, 90.0, 199.5, 3.0, 2.0, 0, 0)"
        )
        conn.commit()
        conn.close()

    def test_depthtolist(self, tmp_path):
        self._create_test_db(tmp_path, "W1")
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            w = Well("W1", 200, 5, 90)
            w.depthtolist()
            assert w.depthlist == [0, 100, 200]
        finally:
            os.chdir(original_dir)

    def test_inctolist(self, tmp_path):
        self._create_test_db(tmp_path, "W2")
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            w = Well("W2", 200, 5, 90)
            w.inctolist()
            assert w.inclist == [0, 2.5, 5.0]
        finally:
            os.chdir(original_dir)

    def test_azitolist(self, tmp_path):
        self._create_test_db(tmp_path, "W3")
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            w = Well("W3", 200, 5, 90)
            w.azitolist()
            assert w.azilist == [0, 45.0, 90.0]
        finally:
            os.chdir(original_dir)


class TestWellMapDbMethods:
    def _create_wellmap_db(self, tmp_path, name):
        """Helper to create a wellmap database."""
        db_path = tmp_path / (name + ".db")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE wellmap(geotvd REAL, latitude REAL, longitude REAL)"
        )
        cursor.execute("INSERT INTO wellmap VALUES(10.0, 29.5, -93.8)")
        cursor.execute("INSERT INTO wellmap VALUES(-100.0, 29.6, -93.7)")
        conn.commit()

        # Also create stratigraphy table for strattolist
        cursor.execute(
            "CREATE TABLE stratigraphy("
            "Depth REAL, Fm_Name TEXT, Fm_Color TEXT,"
            "Fm_TVD REAL, Fm_Inc REAL, Fm_Azi REAL,"
            "Fm_North REAL, Fm_East REAL,"
            "Fm_alt REAL, Fm_lat REAL, Fm_lon REAL)"
        )
        cursor.execute(
            "INSERT INTO stratigraphy VALUES"
            "(0, 'Holocene', '#fef2e0', 0, 0, 0, 0, 0, 10.0, 29.5, -93.8)"
        )
        cursor.execute(
            "INSERT INTO stratigraphy VALUES"
            "(5000, 'Miocene', '#aabbcc', 4800, 0, 0, 0, 0, -4790, 29.6, -93.7)"
        )
        conn.commit()
        conn.close()

    def test_tvdtolist(self, tmp_path):
        self._create_wellmap_db(tmp_path, "WM1")
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            wm = WellMap("WM1", 0, 29.5, -93.8)
            wm.tvdtolist()
            assert wm.tvdlist == [10.0, -100.0]
        finally:
            os.chdir(original_dir)

    def test_lattolist(self, tmp_path):
        self._create_wellmap_db(tmp_path, "WM2")
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            wm = WellMap("WM2", 0, 29.5, -93.8)
            wm.lattolist()
            assert wm.latlist == [29.5, 29.6]
        finally:
            os.chdir(original_dir)

    def test_lontolist(self, tmp_path):
        self._create_wellmap_db(tmp_path, "WM3")
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            wm = WellMap("WM3", 0, 29.5, -93.8)
            wm.lontolist()
            assert wm.lonlist == [-93.8, -93.7]
        finally:
            os.chdir(original_dir)

    def test_strattolist(self, tmp_path):
        self._create_wellmap_db(tmp_path, "WM4")
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            wm = WellMap("WM4", 0, 29.5, -93.8)
            wm.strattolist()
            assert wm.strat_altilist == [10.0, -4790]
            assert wm.strat_latlist == [29.5, 29.6]
            assert wm.strat_lonlist == [-93.8, -93.7]
            assert wm.strat_colorlist == ["#fef2e0", "#aabbcc"]
        finally:
            os.chdir(original_dir)

    def test_add_coordinates_new_db(self, tmp_path):
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            # add_coordinates creates surface table if DB doesn't exist,
            # but always tries to INSERT into wellmap, so pre-create it
            db_path = tmp_path / "WMNew.db"
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(
                "CREATE TABLE wellmap(geotvd REAL, latitude REAL, longitude REAL)"
            )
            conn.commit()
            conn.close()

            wm = WellMap("WMNew", 0, 0, 0)
            wm.add_coordinates(15.0, 30.0, -90.0)
            assert wm.surface_alt == 15.0
            assert wm.surface_lat == 30.0
            assert wm.surface_lon == -90.0
        finally:
            os.chdir(original_dir)

    def test_add_coordinates_existing_db(self, tmp_path):
        self._create_wellmap_db(tmp_path, "WMExist")
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            wm = WellMap("WMExist", 0, 0, 0)
            wm.add_coordinates(20.0, 31.0, -89.0)
            # DB already existed so new row added to wellmap
            conn = sqlite3.connect(str(tmp_path / "WMExist.db"))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM wellmap")
            count = cursor.fetchone()[0]
            assert count == 3  # 2 original + 1 new
            conn.close()
        finally:
            os.chdir(original_dir)

    def test_writedata_negates_tvd(self, tmp_path):
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            wm = WellMap("WMWrite", 0, 0, 0)
            wm.writedata(100.0, 29.5, -93.8)
            # Check that TVD was negated in DB
            db_path = tmp_path / "WMWrite.db"
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM wellmap")
            row = cursor.fetchone()
            assert row[0] == -100.0  # TVD negated
            assert row[1] == 29.5
            assert row[2] == -93.8
            conn.close()
        finally:
            os.chdir(original_dir)
