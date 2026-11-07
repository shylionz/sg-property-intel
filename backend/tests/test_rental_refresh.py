import sys
from pathlib import Path
from datetime import date, datetime
from unittest.mock import patch, Mock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.database import Base, Rental, RentalRefreshStatus, Transaction
from scrapers.project_fetcher import refresh_project_rentals
from scrapers.rentals import fetch_rentals
from api.project import get_rentals, get_analytics

@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()

def record(month=9):
    return dict(project_name='THE ANCHORAGE', street_name='ALEXANDRA ROAD',
                lease_date_parsed=date(datetime.now().year, month, 1), lease_date=f'{month}-26',
                monthly_rent=5000, bedrooms=2, size_band='900-1200')

def seed(db):
    db.add(Rental(**record(4)))
    db.commit()

def test_refresh_updates_existing_rentals_and_preserves_identical_contracts(db):
    db.add(Rental(**record())); db.commit()
    with patch('scrapers.project_fetcher.fetch_rentals', return_value=[record(), record()]) as fetch:
        first = refresh_project_rentals(db, 'THE ANCHORAGE')
        assert first['status'] == 'success'
        assert first['latest_db_month'] == f'{datetime.now().year}-09'
        assert db.query(Rental).count() == 2
        assert refresh_project_rentals(db, 'THE ANCHORAGE')['throttled']
        assert fetch.call_count == 1
        refresh_project_rentals(db, 'THE ANCHORAGE', force=True)
        assert db.query(Rental).count() == 2

def test_failure_empty_wrong_project_and_older_snapshot_preserve_cache(db):
    seed(db)
    for rows in ([], [dict(record(), project_name='OTHER')], [record(1)]):
        with patch('scrapers.project_fetcher.fetch_rentals', return_value=rows):
            assert refresh_project_rentals(db, 'THE ANCHORAGE', force=True)['status'] == 'failed'
        assert db.query(Rental).count() == 1
        assert db.query(Rental).one().lease_date_parsed.month == 4
    with patch('scrapers.project_fetcher.fetch_rentals', side_effect=RuntimeError('timeout')):
        assert refresh_project_rentals(db, 'THE ANCHORAGE', force=True)['status'] == 'failed'
    assert db.query(Rental).count() == 1

def test_insert_failure_rolls_back_replacement(db):
    seed(db)
    with patch('scrapers.project_fetcher.fetch_rentals', return_value=[dict(record(), monthly_rent=10**100)]):
        assert refresh_project_rentals(db, 'THE ANCHORAGE', force=True)['status'] == 'failed'
    assert db.query(Rental).count() == 1

def test_historical_rows_outside_source_window_survive(db):
    old = Rental(**dict(record(), lease_date_parsed=date(2010, 1, 1)))
    db.add(old); db.commit()
    with patch('scrapers.project_fetcher.fetch_rentals', return_value=[record()]):
        assert refresh_project_rentals(db, 'THE ANCHORAGE')['status'] == 'success'
    assert db.query(Rental).count() == 2

def page(first, last, total, count):
    row = '<tr><td>THE ANCHORAGE</td><td>ALEXANDRA ROAD</td><td>03</td><td>Non-Landed Properties</td><td>2</td><td>5,000</td><td>100 to 110</td><td>1,100 to 1,200</td><td>Sep-26</td></tr>'
    return f'<table><tr><th>Project</th></tr>{row * count}</table>Showing {first} to {last} of {total} results'

def source(pages):
    session = Mock(RENTAL_URL='https://example.invalid')
    session.post.side_effect = [Mock(text=html) for html in pages]
    return session

def test_scraper_reads_all_pages_above_old_cap():
    pages = [page(i * 100 + 1, (i + 1) * 100, 1101, 100) for i in range(11)] + [page(1101,1101,1101,1)]
    session = source(pages)
    with patch('scrapers.rentals.URASession', return_value=session), patch('scrapers.rentals.time.sleep'):
        assert len(fetch_rentals('THE ANCHORAGE', year_from=2021, year_to=2026, month_to=11)) == 1101
    assert session.post.call_args_list[0].kwargs['data']['page'] == '1'
    assert session.post.call_args_list[1].kwargs['data']['page'] == '2'
    assert session.post.call_args_list[0].kwargs['data']['locationDetails'] == '["projectName","THE ANCHORAGE"]'

@pytest.mark.parametrize('pages,max_pages', [
    ([page(1,100,101,100), '<html>session expired</html>'],100),
    ([page(1,100,101,100)],1),
    ([page(1,100,101,100),page(1,100,101,100)],100),
    ([page(1,100,101,100),page(101,101,102,1)],100),
])
def test_scraper_refuses_partial_changed_or_repeated_pages(pages,max_pages):
    with patch('scrapers.rentals.URASession', return_value=source(pages)), patch('scrapers.rentals.time.sleep'):
        with pytest.raises(ValueError):
            fetch_rentals('THE ANCHORAGE', year_from=2021, year_to=2026, month_to=11, max_pages=max_pages)

def test_rental_endpoint_refreshes_existing_rows_and_paginates_stably(db):
    seed(db)
    with patch('scrapers.project_fetcher.fetch_rentals', return_value=[record(4)] + [record()] * 104):
        response = get_rentals('THE ANCHORAGE', page=0, per_page=100, force_refresh=False, refresh_data=True, db=db)
    assert response['total'] == 105
    assert len(response['data']) == 100
    assert response['rental_refresh']['status'] == 'success'
    response = get_rentals('THE ANCHORAGE', page=1, per_page=100, force_refresh=False, refresh_data=False, db=db)
    assert len(response['data']) == 5

def test_analytics_contains_independent_sales_and_rental_freshness(db):
    seed(db)
    with patch('api.project.refresh_project_transactions', return_value={'status': 'success', 'latest_db_month': '2026-10'}), patch('scrapers.project_fetcher.fetch_rentals', return_value=[record(4)] + [record()] * 104):
        result = get_analytics('THE ANCHORAGE', force_refresh=False, db=db)
    assert result['refresh']['latest_db_month'] == '2026-10'
    assert result['rental_refresh']['latest_db_month'].endswith('-09')
    assert result['summary']['total_rentals'] == 105
    assert result['rental_trend'][-1]['n'] == 104


def test_backup_is_consistent_and_never_overwritten(tmp_path):
    import sqlite3
    from utils.backup import ensure_rental_backup
    database = tmp_path / "live.db"
    engine = create_engine("sqlite:///" + str(database))
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    seed(session)
    backup_path = ensure_rental_backup(session)
    session.add(Rental(**record())); session.commit()
    assert ensure_rental_backup(session) == backup_path
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert backup.execute("SELECT COUNT(*) FROM rentals").fetchone()[0] == 1
    assert session.query(Rental).count() == 2
    session.close(); engine.dispose()


def test_preserves_history_older_than_ura_published_snapshot(db):
    seed(db)
    with patch('scrapers.project_fetcher.fetch_rentals', return_value=[record()]):
        assert refresh_project_rentals(db, 'THE ANCHORAGE')['status'] == 'success'
    assert db.query(Rental).count() == 2
    assert {row.lease_date_parsed.month for row in db.query(Rental)} == {4, 9}


def test_backup_failure_prevents_replacement(db):
    seed(db)
    with patch('scrapers.project_fetcher.fetch_rentals', return_value=[record()]), patch('scrapers.project_fetcher.ensure_rental_backup', side_effect=OSError('disk full')):
        assert refresh_project_rentals(db, 'THE ANCHORAGE')['status'] == 'failed'
    assert db.query(Rental).count() == 1
    assert db.query(Rental).one().lease_date_parsed.month == 4


def test_new_install_has_no_database_to_back_up(tmp_path):
    from utils.backup import ensure_rental_backup
    engine = create_engine("sqlite:///" + str(tmp_path / "new.db"))
    session = sessionmaker(bind=engine)()
    assert ensure_rental_backup(session) is None
    session.close(); engine.dispose()


def test_startup_backs_up_before_adding_metadata_tables(tmp_path):
    import os, sqlite3, subprocess
    database = tmp_path / "existing.db"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE original_marker (value TEXT)")
        db.execute("INSERT INTO original_marker VALUES ('preserve')")
    env = dict(os.environ, DATABASE_URL="sqlite:///" + str(database))
    result = subprocess.run([sys.executable, "-c", "import main"],
                            cwd=Path(__file__).resolve().parents[1], env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "integrity_check=ok" in result.stderr
    with sqlite3.connect(tmp_path / ".backups/existing-before-rental-refresh-v1.db") as db:
        assert db.execute("SELECT value FROM original_marker").fetchone()[0] == "preserve"
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='rental_refresh_status'").fetchall()
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='rental_refresh_status'").fetchall()
