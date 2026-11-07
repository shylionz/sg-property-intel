"""
Project fetcher for on-demand data fetching.
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from .transactions import fetch_transactions
from .rentals import fetch_rentals
from models.database import Transaction, Rental, ProjectRefreshStatus, RentalRefreshStatus
from utils.parsers import normalise_project_name
from utils.backup import ensure_rental_backup

logger = logging.getLogger("sg_property_intel.refresh")

REFRESH_THROTTLE_MINUTES = 15
_PROJECT_LOCKS: Dict[str, threading.Lock] = {}
_PROJECT_LOCKS_GUARD = threading.Lock()


def _project_lock(project_name: str) -> threading.Lock:
    with _PROJECT_LOCKS_GUARD:
        return _PROJECT_LOCKS.setdefault(project_name, threading.Lock())


def _latest_month(rows, attr: str) -> Optional[str]:
    values = []
    for row in rows:
        value = row.get(attr) if isinstance(row, dict) else getattr(row, attr, None)
        if value:
            values.append(str(value)[:7])
    return max(values) if values else None


def _txn_key_from_record(rec: Dict) -> Tuple:
    """
    Best practical transaction identity available from URA HTML scrape.
    Limitation: the HTML scrape does not expose unit number/block/caveat id, so two
    truly separate same-project transactions with identical month/price/area/PSF/
    floor/type/street will be treated as one row.
    """
    return (
        normalise_project_name(rec.get("project_name", "")),
        str(rec.get("sale_date_parsed") or ""),
        rec.get("transacted_price"),
        rec.get("area_sqft"),
        rec.get("price_psf"),
        rec.get("floor_band") or "",
        rec.get("property_type") or "",
        rec.get("sale_type") or "",
        rec.get("street_name") or "",
    )


def _txn_key_from_model(t: Transaction) -> Tuple:
    return (
        normalise_project_name(t.project_name or ""),
        str(t.sale_date_parsed or ""),
        t.transacted_price,
        t.area_sqft,
        t.price_psf,
        t.floor_band or "",
        t.property_type or "",
        t.sale_type or "",
        t.street_name or "",
    )


def _get_or_create_status(db: Session, project_name: str) -> ProjectRefreshStatus:
    status = db.query(ProjectRefreshStatus).filter(ProjectRefreshStatus.project_name == project_name).first()
    if not status:
        status = ProjectRefreshStatus(project_name=project_name, source="URA_HTML")
        db.add(status)
        db.flush()
    return status


def get_project_refresh_status(db: Session, project_name: str) -> Optional[Dict]:
    normalized = normalise_project_name(project_name)
    status = db.query(ProjectRefreshStatus).filter(ProjectRefreshStatus.project_name == normalized).first()
    if not status:
        return None
    return {
        "project_name": status.project_name,
        "source": status.source,
        "last_refresh_started_at": status.last_refresh_started_at.isoformat() if status.last_refresh_started_at else None,
        "last_refresh_completed_at": status.last_refresh_completed_at.isoformat() if status.last_refresh_completed_at else None,
        "status": status.status,
        "rows_fetched": status.rows_fetched,
        "rows_inserted": status.rows_inserted,
        "rows_updated": status.rows_updated,
        "latest_source_month": status.latest_source_month,
        "latest_db_month": status.latest_db_month,
        "error_message": status.error_message,
    }


def refresh_project_transactions(db: Session, project_name: str, force: bool = False) -> Dict:
    """Refresh one project's URA transaction scrape and upsert into SQLite."""
    normalized = normalise_project_name(project_name)
    lock = _project_lock(normalized)

    with lock:
        status = _get_or_create_status(db, normalized)
        now = datetime.now()
        if (
            not force
            and status.last_refresh_completed_at
            and status.status == "success"
            and now - status.last_refresh_completed_at < timedelta(minutes=REFRESH_THROTTLE_MINUTES)
        ):
            logger.info(
                "project=%s refresh_status=throttled rows_fetched=%s latest_source_month=%s latest_db_month=%s",
                normalized, status.rows_fetched, status.latest_source_month, status.latest_db_month,
            )
            return {**get_project_refresh_status(db, normalized), "throttled": True}

        status.source = "URA_HTML"
        status.last_refresh_started_at = now
        status.status = "running"
        status.error_message = None
        db.commit()

        try:
            txns = fetch_transactions(
                normalized,
                year_from=datetime.now().year - 5,
                month_from=1,
                year_to=datetime.now().year,
                month_to=12,
                max_pages=50,
            )
            latest_source_month = _latest_month(txns, "sale_date_parsed")

            existing = db.query(Transaction).filter(Transaction.project_name == normalized).all()
            existing_by_key = {}
            duplicate_existing = []
            for row in existing:
                key = _txn_key_from_model(row)
                if key in existing_by_key:
                    duplicate_existing.append(row)
                else:
                    existing_by_key[key] = row

            rows_inserted = 0
            rows_updated = 0
            seen_source_keys = set()

            for rec in txns:
                rec["project_name"] = normalise_project_name(rec.get("project_name") or normalized)
                key = _txn_key_from_record(rec)
                if key in seen_source_keys:
                    continue
                seen_source_keys.add(key)

                row = existing_by_key.get(key)
                if row:
                    row.street_name = rec.get("street_name")
                    row.postal_district = rec.get("postal_district")
                    row.market_segment = rec.get("market_segment")
                    row.property_type = rec.get("property_type")
                    row.tenure = rec.get("tenure")
                    row.sale_type = rec.get("sale_type")
                    row.sale_date = rec.get("sale_date")
                    row.sale_date_parsed = rec.get("sale_date_parsed")
                    row.transacted_price = rec.get("transacted_price")
                    row.nett_price = rec.get("nett_price")
                    row.area_sqft = rec.get("area_sqft")
                    row.area_sqft_band = rec.get("area_sqft_band")
                    row.area_sqm = rec.get("area_sqm")
                    row.price_psf = rec.get("price_psf")
                    row.price_psm = rec.get("price_psm")
                    row.floor_band = rec.get("floor_band")
                    row.number_of_units = rec.get("number_of_units")
                    row.size_band = rec.get("size_band")
                    rows_updated += 1
                else:
                    db.add(Transaction(
                        project_name=rec.get("project_name"), street_name=rec.get("street_name"),
                        postal_district=rec.get("postal_district"), market_segment=rec.get("market_segment"),
                        property_type=rec.get("property_type"), tenure=rec.get("tenure"),
                        sale_type=rec.get("sale_type"), sale_date=rec.get("sale_date"),
                        sale_date_parsed=rec.get("sale_date_parsed"), transacted_price=rec.get("transacted_price"),
                        nett_price=rec.get("nett_price"), area_sqft=rec.get("area_sqft"),
                        area_sqft_band=rec.get("area_sqft_band"), area_sqm=rec.get("area_sqm"),
                        price_psf=rec.get("price_psf"), price_psm=rec.get("price_psm"),
                        floor_band=rec.get("floor_band"), number_of_units=rec.get("number_of_units"),
                        size_band=rec.get("size_band"),
                    ))
                    rows_inserted += 1

            for dup in duplicate_existing:
                db.delete(dup)

            db.flush()
            latest_db_month = db.query(func.max(Transaction.sale_date_parsed)).filter(Transaction.project_name == normalized).scalar()
            latest_db_month_str = str(latest_db_month)[:7] if latest_db_month else None

            status.last_refresh_completed_at = datetime.now()
            status.status = "success"
            status.rows_fetched = len(txns)
            status.rows_inserted = rows_inserted
            status.rows_updated = rows_updated
            status.latest_source_month = latest_source_month
            status.latest_db_month = latest_db_month_str
            status.error_message = None
            db.commit()

            logger.info(
                "project=%s rows_fetched=%s latest_source_month=%s rows_inserted=%s rows_updated=%s duplicates_removed=%s latest_db_month=%s refresh_status=success",
                normalized, len(txns), latest_source_month, rows_inserted, rows_updated, len(duplicate_existing), latest_db_month_str,
            )
            return {**get_project_refresh_status(db, normalized), "throttled": False, "duplicates_removed": len(duplicate_existing)}

        except Exception as e:
            db.rollback()
            status = _get_or_create_status(db, normalized)
            latest_db_month = db.query(func.max(Transaction.sale_date_parsed)).filter(Transaction.project_name == normalized).scalar()
            latest_db_month_str = str(latest_db_month)[:7] if latest_db_month else None
            status.last_refresh_completed_at = datetime.now()
            status.status = "failed"
            status.latest_db_month = latest_db_month_str
            status.error_message = str(e)[:1000]
            db.commit()
            logger.exception("project=%s refresh_status=failed latest_db_month=%s error=%s", normalized, latest_db_month_str, e)
            return {**get_project_refresh_status(db, normalized), "throttled": False}


def refresh_project_rentals(db: Session, project_name: str, force: bool = False) -> Dict:
    """Atomically replace only a fully validated source window, retaining multiplicity.

    URA exposes no contract identifier. Two identical rows can represent two real
    contracts, so a complete snapshot is safer than deduplicating by visible fields.
    Historical rows outside the source window are retained.
    """
    normalized = normalise_project_name(project_name)
    with _project_lock("rentals:" + normalized):
        # End any read transaction opened before waiting for another refresher.
        db.commit()
        status = db.get(RentalRefreshStatus, normalized)
        now = datetime.utcnow()
        if status and not force and status.last_refresh_completed_at:
            cooldown = 15 if status.status == "success" else 1
            if now - status.last_refresh_completed_at < timedelta(minutes=cooldown):
                return {**_rental_status(status), "throttled": True}
        if not status:
            status = RentalRefreshStatus(project_name=normalized, source="URA_HTML")
            db.add(status)
        status.last_refresh_started_at = now
        status.status = "running"
        status.error_message = None
        db.commit()
        try:
            from datetime import date
            start = date(now.year - 5, 1, 1)
            end = date(now.year, now.month, 1)
            rents = fetch_rentals(normalized, year_from=start.year, month_from=start.month,
                                  year_to=end.year, month_to=end.month)
            if not rents:
                raise ValueError("No validated rental snapshot; keeping cached records")
            if any(normalise_project_name(rec.get("project_name", "")) != normalized
                   or not rec.get("lease_date_parsed")
                   or not start <= rec["lease_date_parsed"] <= end
                   or not rec.get("monthly_rent") or rec["monthly_rent"] <= 0 for rec in rents):
                raise ValueError("Invalid rental snapshot; keeping cached records")
            latest = _latest_month(rents, "lease_date_parsed")
            previous_latest = db.query(func.max(Rental.lease_date_parsed)).filter(
                Rental.project_name == normalized).scalar()
            if previous_latest and latest < str(previous_latest)[:7]:
                raise ValueError("URA rental snapshot is older than cached records")
            # URA may enforce a rolling retention window narrower than the
            # requested range. Keep older cached history rather than silently
            # deleting records the source no longer publishes.
            replace_from = max(start, min(rec["lease_date_parsed"] for rec in rents))
            ensure_rental_backup(db)
            db.query(Rental).filter(Rental.project_name == normalized,
                                   Rental.lease_date_parsed >= replace_from,
                                   Rental.lease_date_parsed <= end).delete(synchronize_session=False)
            for rec in rents:
                fields = {key: value for key, value in rec.items() if key in Rental.__table__.columns
                          and key not in ("id", "fetched_at")}
                fields["project_name"] = normalized
                db.add(Rental(**fields))
            db.flush()
            status.status = "success"
            status.rows_fetched = len(rents)
            status.rows_inserted = len(rents)
            status.rows_updated = 0
            status.latest_source_month = latest
            status.latest_db_month = str(db.query(func.max(Rental.lease_date_parsed)).filter(
                Rental.project_name == normalized).scalar())[:7]
            status.last_refresh_completed_at = datetime.utcnow()
            db.commit()
        except Exception as exc:
            db.rollback()
            status = db.get(RentalRefreshStatus, normalized)
            status.status = "failed"
            status.error_message = str(exc)[:1000]
            status.last_refresh_completed_at = datetime.utcnow()
            latest = db.query(func.max(Rental.lease_date_parsed)).filter(Rental.project_name == normalized).scalar()
            status.latest_db_month = str(latest)[:7] if latest else None
            db.commit()
            logger.exception("Rental refresh failed for %s", normalized)
        return {**_rental_status(status), "throttled": False}


def _rental_status(status) -> Dict:
    result = {key: getattr(status, key) for key in (
        "project_name", "source", "status", "rows_fetched", "rows_inserted", "rows_updated",
        "latest_source_month", "latest_db_month", "error_message")}
    for key in ("last_refresh_started_at", "last_refresh_completed_at"):
        value = getattr(status, key)
        result[key] = value.isoformat() + "Z" if value else None
    return result


def fetch_project_data(project_name: str, db: Session) -> Dict:
    normalized = normalise_project_name(project_name)
    refresh = refresh_project_transactions(db, normalized, force=True)
    rental_refresh = refresh_project_rentals(db, normalized, force=True)
    return {
        "project": normalized,
        "transactions": db.query(Transaction).filter(Transaction.project_name == normalized).count(),
        "rentals": db.query(Rental).filter(Rental.project_name == normalized).count(),
        "status": "failed" if any(s.get("status") == "failed" for s in (refresh, rental_refresh)) else "success",
        "refresh": refresh,
        "rental_refresh": rental_refresh,
    }
