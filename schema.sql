
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS movies (
    movie_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    release_year INTEGER,
    imdb_id TEXT,
    director TEXT,
    plot TEXT,
    box_office_usd REAL,
    imdb_rating REAL,
    omdb_response_status TEXT NOT NULL DEFAULT 'PENDING',
    omdb_last_error TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS genres (
    genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (movie_id, genre_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
        ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(genre_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ratings (
    rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    rating REAL NOT NULL CHECK (rating >= 0.5 AND rating <= 5.0),
    rated_at TEXT NOT NULL,
    rated_at_unix INTEGER NOT NULL,
    UNIQUE (user_id, movie_id, rated_at_unix),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS omdb_cache (
    cache_key TEXT PRIMARY KEY,
    response_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ratings_movie_id
    ON ratings(movie_id);

CREATE INDEX IF NOT EXISTS idx_ratings_user_id
    ON ratings(user_id);

CREATE INDEX IF NOT EXISTS idx_movies_release_year
    ON movies(release_year);

CREATE INDEX IF NOT EXISTS idx_movies_director
    ON movies(director);

CREATE INDEX IF NOT EXISTS idx_movie_genres_genre_id
    ON movie_genres(genre_id);
