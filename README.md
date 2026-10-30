
# Movie Data Pipeline

## 1. Project Overview

This project implements a Python ETL pipeline for the tsworks Data Engineer assignment. It combines movie and rating data from the MovieLens Small dataset with additional movie information from the OMDb API.

The cleaned data is stored in a SQLite relational database and analyzed using SQL.

## 2. Technologies Used

- Python
- pandas
- requests
- python-dotenv
- SQLite
- SQL
- Git and GitHub

## 3. Architecture

1. Extract movie and rating data from CSV files.
2. Clean invalid rows, convert data types, and parse release years.
3. Enrich movie details using the OMDb API.
4. Normalize genres into separate relational tables.
5. Load movies, genres, ratings, and cached API responses into SQLite.
6. Execute SQL queries to answer analytical questions.

## 4. Project Structure

```text
movie_data_pipeline_tsworks/
├── data/
│   ├── movies.csv
│   └── ratings.csv
├── etl.py
├── schema.sql
├── queries.sql
├── requirements.txt
├── README.md
├── .env
└── .gitignore
```

Do not commit `.env` or downloaded CSV files to GitHub.

## 5. Setup Instructions

1. Install Python 3.10 or later.
2. Download and extract the MovieLens Small dataset.
3. Place `movies.csv` and `ratings.csv` inside the `data` folder.
4. Create a virtual environment:

   `python -m venv .venv`

5. Activate it on Windows:

   `.\.venv\Scripts\Activate.ps1`

6. Install dependencies:

   `python -m pip install -r requirements.txt`

7. Create `.env` in the project root and add your OMDb API key.

## 6. Running the Pipeline

First, test CSV ingestion and database loading without API calls:

`python etl.py --skip-api`

Test a limited number of API requests:

`python etl.py --max-api-calls 20`

Run the pipeline:

`python etl.py`

Check your OMDb quota before full enrichment. Repeated runs reuse cached API responses.

## 7. Database Design

- `movies`: movie details and API enrichment.
- `genres`: distinct movie genres.
- `movie_genres`: many-to-many movie/genre relationship.
- `ratings`: user ratings and timestamps.
- `omdb_cache`: saved API responses.

Primary keys, foreign keys, unique constraints, and indexes support data integrity and query performance.

## 8. Analytical Questions

The `queries.sql` file answers:

1. Which movie has the highest average rating?
2. Which five genres have the highest average rating?
3. Which director has the most movies?
4. What is the average movie rating for each release year?

## 9. Data Quality and Reliability

- Invalid and duplicate source rows are handled.
- Ratings are checked against the expected range.
- Missing API details remain null.
- API responses are cached.
- Requests use timeouts and retry logic.
- Unique constraints prevent duplicate movie and rating records.
- API statuses help identify incomplete enrichment.

## 10. Assumptions and Limitations

- MovieLens `movieId` is the movie's primary identifier.
- OMDb is queried by title and, where available, release year.
- Not every MovieLens title will match OMDb.
- Box office and director information can be unavailable.
- The API quota may prevent full enrichment in one run.
- Director analysis can be incomplete when some movies lack API details.
- SQLite is used because this is a small assignment.

## 11. Future Improvements

- Add structured logging and automated tests.
- Improve movie matching with IMDb identifiers where available.
- Schedule regular pipeline runs.
- Add monitoring and alerts for failed API requests.
- Use PostgreSQL or a cloud data warehouse for production workloads.
- Add data validation and quality reports.

## 12. Challenges and Solutions

Challenge: OMDb API request limit

During execution, the OMDb API returned a request-limit error. This prevented further movie enrichment.

Solution:

The ETL script was updated to identify API request-limit errors separately from invalid API keys. It now stops enrichment gracefully instead of terminating unexpectedly. Previously processed database records are preserved.

## 13.Execution Results

The pipeline successfully loaded the MovieLens dataset.
Dataset loading results:

Total movies loaded: 9,742

Total valid rating records: 100,836

API matches: 1,292

Movies not found in OMDb: 706

New API requests in the latest run: 1

## 14.OMDb API Integration and Error Handling

The project integrates the OMDb API to enrich movie records with additional information, such as movie details, director, release year, genre and other available metadata.

The following features are implemented:

1.API requests using movie titles and release years.
2.Response caching to avoid unnecessary repeated API requests.
3.Handling of movies that are not found in OMDb.
4.Retry handling for temporary request failures.
5.Detection of API request-limit errors.
6.Graceful stopping when the API request limit is reached.
7.Database commits to preserve processed records.

## 15. Learning Outcomes

Through this project, I gained practical experience in:

1.Building an ETL pipeline using Python.

2.Working with CSV datasets and Pandas.

3.Integrating external APIs.

4.Designing relational database schemas.

5.Writing SQL analytical queries.

6.Handling API errors and request limits.

7.Managing project files using Git and GitHub.

## 16.Conclusion

This project demonstrates the implementation of a simple end-to-end movie data pipeline. It combines data extraction, transformation, API-based enrichment, relational database storage, and SQL analytics.

The project provided practical exposure to important data engineering concepts and helped develop an understanding of how structured data pipelines are built and managed.