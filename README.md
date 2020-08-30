# IMDB Top Ranked Films Scraper

This is a simple Python script that uses the Beautiful Soup library to scrape IMDB's list of Top 1000 films.

It produces 2 output CSV files:

> top_films_list.csv

> aggregation_summary.csv

The first file is the entire list of top 1000 films ranked by rating on IMDB:
 
The second file is the top 1000 films aggregated by each year, starting from 1900:

This second file also contains the total number of films listed on IMDB for each year. This allows you to see what percentage
of these films feature in the top 1000.

