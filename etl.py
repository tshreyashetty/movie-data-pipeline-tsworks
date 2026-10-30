
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "movie_data.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"
OMDB_URL = "https://www.omdbapi.com/"


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_title_year(raw_title):
    """Extract year from titles such as Toy Story (1995)."""
    title = str(raw_title).strip()
    match = re.search(r"\((\d{4})\)\s*$", title)
    year = int(match.group(1)) if match else None
    if match:
        title = title[:match.start()].strip()
    return title, year


def parse_number(value):
    """Convert valid numbers to float and missing values to None."""
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    if text.upper() in {"", "N/A", "NA", "NONE", "NULL"}:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def parse_box_office(value):
    """Convert '$100,000,000' into 100000000.0."""
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    if text.upper() in {"", "N/A", "NA", "NONE", "NULL"}:
        return None

    cleaned = re.sub(r"[^0-9.]", "", text)

    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def load_csvs(data_dir):
    movies_path = data_dir / "movies.csv"
    ratings_path = data_dir / "ratings.csv"

    if not movies_path.exists() or not ratings_path.exists():
        raise FileNotFoundError(
            f"Put movies.csv and ratings.csv inside: {data_dir}"
        )

    movies = pd.read_csv(movies_path, sep="\t")
    ratings = pd.read_csv(ratings_path, sep="\t")

    required_movies = {"movieId", "title", "genres"}
    required_ratings = {
        "userId", "movieId", "rating", "timestamp"
    }

    if not required_movies.issubset(movies.columns):
        raise ValueError(
            f"movies.csv requires columns: {sorted(required_movies)}"
        )

    if not required_ratings.issubset(ratings.columns):
        raise ValueError(
            f"ratings.csv requires columns: {sorted(required_ratings)}"
        )

    movies = movies.drop_duplicates(
        subset=["movieId"]
    ).copy()

    ratings = ratings.drop_duplicates(
        subset=["userId", "movieId", "timestamp"]
    ).copy()

    movies["movieId"] = pd.to_numeric(
        movies["movieId"], errors="coerce"
    )

    ratings["movieId"] = pd.to_numeric(
        ratings["movieId"], errors="coerce"
    )

    ratings["userId"] = pd.to_numeric(
        ratings["userId"], errors="coerce"
    )

    ratings["rating"] = pd.to_numeric(
        ratings["rating"], errors="coerce"
    )

    ratings["timestamp"] = pd.to_numeric(
        ratings["timestamp"], errors="coerce"
    )

    movies = movies.dropna(
        subset=["movieId", "title"]
    )

    ratings = ratings.dropna(
        subset=["userId", "movieId", "rating", "timestamp"]
    )

    ratings = ratings[
        ratings["rating"].between(0.5, 5.0)
    ]

    movies["movieId"] = movies["movieId"].astype(int)
    ratings["movieId"] = ratings["movieId"].astype(int)
    ratings["userId"] = ratings["userId"].astype(int)
    ratings["timestamp"] = ratings["timestamp"].astype(int)

    return movies, ratings


def connect_db(db_path):
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    conn.executescript(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    conn.commit()

    return conn


def get_cached_response(conn, cache_key):
    row = conn.execute(
        """
        SELECT response_json
        FROM omdb_cache
        WHERE cache_key = ?
        """,
        (cache_key,)
    ).fetchone()

    if row is None:
        return None

    try:
        return json.loads(row["response_json"])
    except json.JSONDecodeError:
        return None


def save_cached_response(conn, cache_key, payload):
    conn.execute(
        """
        INSERT INTO omdb_cache(
            cache_key, response_json, fetched_at
        )
        VALUES (?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            response_json = excluded.response_json,
            fetched_at = excluded.fetched_at
        """,
        (cache_key, json.dumps(payload), now_utc())
    )

    conn.commit()


def fetch_omdb(
    conn, title, year, api_key, timeout, retries, delay
):
    """Fetch OMDb data and distinguish quota errors from invalid keys."""

    cache_key = f"{title.casefold()}|{year or ''}"
    cached = get_cached_response(conn, cache_key)

    if cached is not None:
        status = (
            "FOUND" if cached.get("Response") == "True"
            else "NOT_FOUND"
        )
        return cached, status, False

    params = {
        "apikey": api_key,
        "t": title,
        "type": "movie"
    }

    if year:
        params["y"] = str(year)

    for attempt in range(retries + 1):
        try:
            response = requests.get(
                OMDB_URL,
                params=params,
                timeout=timeout
            )

            try:
                payload = response.json()
            except ValueError:
                payload = {}

            if not isinstance(payload, dict):
                return {
                    "_error": "OMDb returned a non-JSON response"
                }, "INVALID_RESPONSE", True

            api_error = str(
                payload.get("Error", "")
            ).strip()

            if "request limit reached" in api_error.lower():
                return {
                    "_error": api_error
                }, "API_LIMIT_ERROR", True

            if response.status_code in (401, 403):
                return {
                    "_error": api_error or
                    f"HTTP {response.status_code}"
                }, "API_KEY_ERROR", True

            response.raise_for_status()

            save_cached_response(
                conn, cache_key, payload
            )

            status = (
                "FOUND"
                if payload.get("Response") == "True"
                else "NOT_FOUND"
            )

            time.sleep(max(0, delay))

            return payload, status, True

        except (
            requests.Timeout,
            requests.ConnectionError,
            requests.HTTPError,
            ValueError
        ) as exc:

            if attempt == retries:
                return {
                    "_error": str(exc)
                }, "API_ERROR", True

            time.sleep(min(2 ** attempt, 8))

    return None, "API_ERROR", True


def upsert_movie(
    conn, movie_id, raw_title, genres_value, payload, status
):
    title, title_year = parse_title_year(raw_title)
    payload = payload or {}

    year_match = re.search(
        r"\b(\d{4})\b",
        str(payload.get("Year", ""))
    )

    api_year = (
        int(year_match.group(1))
        if year_match else None
    )

    release_year = title_year or api_year

    def clean_text(value):
        if not value or str(value).strip().upper() in {
            "N/A", "NA"
        }:
            return None

        return str(value).strip()

    director = clean_text(payload.get("Director"))
    plot = clean_text(payload.get("Plot"))
    imdb_id = clean_text(payload.get("imdbID"))

    box_office = parse_box_office(
        payload.get("BoxOffice")
    )

    imdb_rating = parse_number(
        payload.get("imdbRating")
    )

    last_error = payload.get("_error")

    conn.execute(
        """
        INSERT INTO movies (
            movie_id, title, release_year, imdb_id,
            director, plot, box_office_usd, imdb_rating,
            omdb_response_status, omdb_last_error, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(movie_id) DO UPDATE SET
            title = excluded.title,
            release_year = excluded.release_year,
            imdb_id = COALESCE(
                excluded.imdb_id, movies.imdb_id
            ),
            director = COALESCE(
                excluded.director, movies.director
            ),
            plot = COALESCE(
                excluded.plot, movies.plot
            ),
            box_office_usd = COALESCE(
                excluded.box_office_usd,
                movies.box_office_usd
            ),
            imdb_rating = COALESCE(
                excluded.imdb_rating,
                movies.imdb_rating
            ),
            omdb_response_status =
                excluded.omdb_response_status,
            omdb_last_error = excluded.omdb_last_error,
            updated_at = excluded.updated_at
        """,
        (
            movie_id,
            title,
            release_year,
            imdb_id,
            director,
            plot,
            box_office,
            imdb_rating,
            status,
            last_error,
            now_utc()
        )
    )

    # Normalize the pipe-separated genres.
    conn.execute(
        "DELETE FROM movie_genres WHERE movie_id = ?",
        (movie_id,)
    )

    raw_genres = str(genres_value or "")

    for genre in (
        g.strip() for g in raw_genres.split("|")
    ):
        if not genre or genre.lower() in {
            "(no genres listed)", "nan", "none"
        }:
            continue

        conn.execute(
            "INSERT OR IGNORE INTO genres(genre_name) VALUES (?)",
            (genre,)
        )

        genre_row = conn.execute(
            """
            SELECT genre_id
            FROM genres
            WHERE genre_name = ?
            """,
            (genre,)
        ).fetchone()

        conn.execute(
            """
            INSERT OR IGNORE INTO movie_genres(
                movie_id, genre_id
            )
            VALUES (?, ?)
            """,
            (movie_id, genre_row["genre_id"])
        )


def load_ratings(conn, ratings):
    rows = []

    for row in ratings.itertuples(index=False):
        timestamp = int(row.timestamp)

        try:
            rated_at = datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc
            ).isoformat(timespec="seconds")

        except (OverflowError, OSError, ValueError):
            continue

        rows.append((
            int(row.userId),
            int(row.movieId),
            float(row.rating),
            rated_at,
            timestamp
        ))

    conn.executemany(
        """
        INSERT OR IGNORE INTO ratings(
            user_id, movie_id, rating,
            rated_at, rated_at_unix
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        rows
    )

    conn.commit()

    return len(rows)


def main():
    parser = argparse.ArgumentParser(
        description="MovieLens to SQLite ETL with OMDb enrichment"
    )

    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Load CSV data without calling OMDb"
    )

    parser.add_argument(
        "--max-api-calls",
        type=int,
        default=None,
        help="Maximum new API requests for this run"
    )

    args = parser.parse_args()

    load_dotenv(BASE_DIR / ".env")

    api_key = os.getenv("OMDB_API_KEY", "").strip()
    timeout = int(
        os.getenv("OMDB_TIMEOUT_SECONDS", "15")
    )
    retries = int(
        os.getenv("OMDB_MAX_RETRIES", "3")
    )
    delay = float(
        os.getenv("OMDB_REQUEST_DELAY_SECONDS", "0.25")
    )

    if not args.skip_api and not api_key:
        print(
            "ERROR: Add your API key to .env, or use --skip-api.",
            file=sys.stderr
        )
        return 2

    conn = None

    try:
        movies, ratings = load_csvs(DATA_DIR)
        conn = connect_db(DB_PATH)

        print(
            f"Loaded {len(movies):,} movies and "
            f"{len(ratings):,} valid rating rows."
        )

        api_calls = 0
        found = 0
        not_found = 0
        api_errors = 0

        for i, row in enumerate(
            movies.itertuples(index=False),
            start=1
        ):
            movie_id = int(row.movieId)
            raw_title = str(row.title)

            genre_string = (
                str(row.genres)
                if pd.notna(row.genres)
                else ""
            )

            title, year = parse_title_year(raw_title)
            payload = None

            if args.skip_api:
                status = "SKIPPED"

            else:
                cache_key = (
                    f"{title.casefold()}|{year or ''}"
                )

                cached = get_cached_response(
                    conn, cache_key
                )

                if (
                    cached is None
                    and args.max_api_calls is not None
                    and api_calls >= args.max_api_calls
                ):
                    status = "PENDING"

                else:
                    payload, status, made_request = fetch_omdb(
                        conn,
                        title,
                        year,
                        api_key,
                        timeout,
                        retries,
                        delay
                    )

                    if made_request:
                        api_calls += 1

                    if status in {
                        "API_LIMIT_ERROR",
                        "API_KEY_ERROR"
                    }:
                        error_message = (payload or {}).get(
                            "_error",
                            "Unknown OMDb error"
                        )

                        # Preserve the current movie as pending.
                        upsert_movie(
                            conn,
                            movie_id,
                            raw_title,
                            genre_string,
                            payload,
                            "PENDING"
                        )

                        conn.commit()

                        if status == "API_LIMIT_ERROR":
                            print(
                                "OMDb request limit reached: "
                                f"{error_message}",
                                file=sys.stderr
                            )
                        else:
                            print(
                                "Invalid OMDb API key: "
                                f"{error_message}",
                                file=sys.stderr
                            )

                        print(
                            "Stopping API enrichment safely."
                        )

                        break

            upsert_movie(
                conn,
                movie_id,
                raw_title,
                genre_string,
                payload,
                status
            )

            if status == "FOUND":
                found += 1

            elif status == "NOT_FOUND":
                not_found += 1

            elif status in {
                "API_ERROR",
                "INVALID_RESPONSE"
            }:
                api_errors += 1

            if i % 500 == 0 or i == len(movies):
                conn.commit()

                print(
                    f"Processed {i:,}/{len(movies):,} movies; "
                    f"new API requests: {api_calls:,}"
                )

        ratings_processed = load_ratings(
            conn, ratings
        )

        print("\nETL summary")
        print(f"Movies: {len(movies):,}")
        print(f"Source rating rows: {len(ratings):,}")
        print(
            f"Rating rows processed: {ratings_processed:,}"
        )
        print(f"New API requests: {api_calls:,}")
        print(f"API matches this run: {found:,}")
        print(f"Not found: {not_found:,}")
        print(f"API errors: {api_errors:,}")
        print(f"Database: {DB_PATH}")
        print("ETL processing finished.")

        return 0

    except (
        FileNotFoundError,
        ValueError,
        sqlite3.Error
    ) as exc:

        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
