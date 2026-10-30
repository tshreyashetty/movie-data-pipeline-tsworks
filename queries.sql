-- 1. Which movie has the highest average rating?
SELECT
    m.movie_id,
    m.title,
    ROUND(AVG(r.rating), 3) AS average_rating,
    COUNT(*) AS rating_count
FROM movies AS m
JOIN ratings AS r
    ON r.movie_id = m.movie_id
GROUP BY m.movie_id, m.title
ORDER BY
    average_rating DESC,
    rating_count DESC,
    m.title ASC
LIMIT 1;


-- Optional alternative: require at least 50 ratings.
-- This avoids ranking a movie highly based on just one vote.
SELECT
    m.movie_id,
    m.title,
    ROUND(AVG(r.rating), 3) AS average_rating,
    COUNT(*) AS rating_count
FROM movies AS m
JOIN ratings AS r
    ON r.movie_id = m.movie_id
GROUP BY m.movie_id, m.title
HAVING COUNT(*) >= 50
ORDER BY average_rating DESC, rating_count DESC
LIMIT 1;


-- 2. Top 5 genres by average rating.
SELECT
    g.genre_name,
    ROUND(AVG(r.rating), 3) AS average_rating,
    COUNT(*) AS rating_count
FROM genres AS g
JOIN movie_genres AS mg
    ON mg.genre_id = g.genre_id
JOIN ratings AS r
    ON r.movie_id = mg.movie_id
GROUP BY g.genre_id, g.genre_name
ORDER BY
    average_rating DESC,
    rating_count DESC,
    g.genre_name ASC
LIMIT 5;


-- 3. Director with the most movies.
SELECT
    director,
    COUNT(*) AS movie_count
FROM movies
WHERE director IS NOT NULL
  AND TRIM(director) <> ''
  AND LOWER(director) <> 'n/a'
GROUP BY director
ORDER BY movie_count DESC, director ASC
LIMIT 1;


-- 4. Average rating by release year.
SELECT
    m.release_year,
    ROUND(AVG(r.rating), 3) AS average_rating,
    COUNT(*) AS rating_count,
    COUNT(DISTINCT m.movie_id) AS movie_count
FROM movies AS m
JOIN ratings AS r
    ON r.movie_id = m.movie_id
WHERE m.release_year IS NOT NULL
GROUP BY m.release_year
ORDER BY m.release_year;


-- Data quality checks.
SELECT COUNT(*) AS movie_count FROM movies;

SELECT COUNT(*) AS rating_count FROM ratings;

SELECT
    omdb_response_status,
    COUNT(*) AS movie_count
FROM movies
GROUP BY omdb_response_status;

SELECT COUNT(*) AS invalid_rating_count
FROM ratings
WHERE rating < 0.5 OR rating > 5.0;
