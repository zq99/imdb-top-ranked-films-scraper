import csv
import datetime
import math
import statistics as stat
import logging

import requests
import validators
from bs4 import BeautifulSoup

log = logging.getLogger("imdb scraper")
logging.basicConfig(level = logging.INFO)


def connect_to_url(page_url):
    try:
        page = requests.get(page_url)
        return page
    except ConnectionError as e:
        log.error(e)


def is_valid_page(page):
    return page is not None and page.status_code == 200


def page_error_info(page_url, page):
    code = str(page.status_code) if page is not None else "---"
    return "status code={} - website error for: {}".format(code, page_url)


def is_file_open(file_name):
    try:
        fs = open(file_name, mode='w', newline='')
        fs.close()
        return False
    except PermissionError as e:
        log.error(e)
        return True


class YearInfo:
    def __init__(self, film_year, year_meta_data, total_count_in_year, total_count_in_year_text):
        self.year_meta_data = year_meta_data
        self.film_year = film_year
        self.total_count_in_year = total_count_in_year
        self.total_count_in_year_text = total_count_in_year_text
        self.top_film_count = 0
        self.top_film_rating_total = 0.0
        self.rating_values_list = []
        self.top_10_count = 0
        self.top_20_count = 0
        self.top_50_count = 0
        self.top_100_count = 0
        self.top_250_count = 0
        self.top_500_count = 0

    def get_standard_dev_ratings(self):
        return stat.pstdev(self.rating_values_list) if len(self.rating_values_list) > 0 else 0

    def get_average_rating(self):
        return round(float(self.top_film_rating_total) / float(self.top_film_count),
                     2) if self.top_film_count > 0 else 0.0

    def get_percentage_top_films_in_year(self):
        return float(self.top_film_count) / float(self.total_count_in_year) if self.total_count_in_year > 0 else 0

    def get_percentage_top_films_in_1000(self):
        return float(self.top_film_count) / float(1000)

    def get_decade(self):
        year = int(self.film_year)
        return "{}{}".format(math.floor(year / 10), "0")


class Film:
    def __init__(self, film_title, film_year, rating, url):
        self.film_title = film_title
        self.film_year = film_year
        self.rating = rating
        self.url = url

    def to_string(self):
        return "title={} year={} rating={}".format(self.film_title, self.film_year, self.rating)

    def get_rating_value(self):
        return float(self.rating)


def get_year_info(year, year_data):
    film_count_in_year_text = get_film_count_in_year_text(year_data)
    film_count_in_year_value = get_film_count_in_year_value(year_data)
    return YearInfo(year, year_data, film_count_in_year_value, film_count_in_year_text)


def get_film_count_in_year_text(year_data):
    return (year_data.replace("1-50 of", "").replace("titles.", "")).strip()


def get_film_count_in_year_value(year_data):
    year_text = get_film_count_in_year_text(year_data)
    year_text = year_text.replace(",", "")
    return int(year_text) if year_text.isnumeric() else 0


def get_title_count(page_url):
    year_info = ""
    page = connect_to_url(page_url)
    if not is_valid_page(page):
        log.warning(page_error_info(page_url, page))
        return year_info
    soup = BeautifulSoup(page.text, 'html.parser')
    desc_data = soup.find_all('div', "desc")
    if desc_data:
        span_text = desc_data[0].find_all('span')
        if span_text:
            year_info = span_text[0].getText()
    return year_info


def get_file(file_name):
    if is_file_open(file_name):
        log.warning("Unable to output data. File is open : {}".format(file_name))
        return
    log_file = open(file_name, mode='w', newline='', encoding="utf-8")
    return log_file


def export_top_film_list(film_list):
    file_name = "top_films_list.csv"
    export_file = get_file(file_name)
    if export_file:
        with export_file:
            log.info("exporting : {}".format(file_name))
            export_writer = csv.writer(export_file, delimiter=',')
            export_writer.writerow(["rank", "film_title", "film_year", "film_rating", "link_url"])
            rank = 1
            if film_list:
                for film in film_list:
                    export_writer.writerow([rank, film.film_title, film.film_year, film.get_rating_value(), film.url])
                    rank += 1


def export_aggregation_summary(year_dict):
    file_name = "aggregation_summary.csv"
    export_file = get_file(file_name)
    if export_file:
        with export_file:
            log.info("exporting : {}".format(file_name))
            export_writer = csv.writer(export_file, delimiter=',')
            export_writer.writerow(["release_year", "decade_start_year", "total_count_in_IMDB",
                                    "top_1000_count", "top_1000_rating_total", "top_1000_average_rating",
                                    "percentage_of_year_total", "percentage_of_top_1000","top_1000_std_dev_ratings",
                                    "top_10_count", "top_20_count", "top_50_count",
                                    "top_100_count", "top_250_count", "top_500_count"])
            for key in year_dict:
                export_writer.writerow([key,
                                        year_dict[key].get_decade(),
                                        year_dict[key].total_count_in_year,
                                        year_dict[key].top_film_count,
                                        year_dict[key].top_film_rating_total,
                                        year_dict[key].get_average_rating(),
                                        year_dict[key].get_percentage_top_films_in_year(),
                                        year_dict[key].get_percentage_top_films_in_1000(),
                                        year_dict[key].get_standard_dev_ratings(),
                                        year_dict[key].top_10_count,
                                        year_dict[key].top_20_count,
                                        year_dict[key].top_50_count,
                                        year_dict[key].top_100_count,
                                        year_dict[key].top_250_count,
                                        year_dict[key].top_500_count])


def get_total_film_counts():
    # retrieves the number of movies listed on
    # IMDB in each year since 1900 up to the current year

    now = datetime.datetime.now()
    year_dict = {}
    main_url = "https://www.imdb.com/search/title/?year={}&title_type=feature&"
    earliest_year = 1900
    latest_year = now.year
    for year in range(latest_year, earliest_year, -1):
        url = main_url.format(year)
        log.info("processing : " + url)
        if validators.url(url):
            year_data = get_title_count(url)
            year_info = get_year_info(year, year_data)
            year_dict[year] = year_info
    return year_dict


def get_film_info_from_page(page_url):
    log.info("processing : " + page_url)
    results = []
    page = connect_to_url(page_url)
    if not is_valid_page(page):
        log.error(page_error_info(page_url, page))
        return results

    soup = BeautifulSoup(page.text, 'html.parser')
    list_data = soup.find_all('div', 'lister-list')
    if list_data:
        list_item = list_data[0].find_all('div', 'lister-item mode-simple')
        if list_item:
            for l in list_item:
                title_name = l.find('div', 'col-title')
                title_name = title_name.find('a').getText().strip()
                rating = l.find('div', 'col-imdb-rating').getText().strip()
                year = l.find('span', 'lister-item-year text-muted unbold').getText().strip()
                year = (year.replace('(', '')).replace(')', '')
                year = year[-4:]
                url_tag = l.find("a")
                url = ""
                if url_tag:
                    url = "https://www.imdb.com" + url_tag['href']
                info = Film(title_name, year, rating, url)
                results.append(info)
    return results


def next_page_url(counter):
    return "&start={}&ref_=adv_nxt".format(counter + 1)


def get_top_film_list():
    top_list = []
    main_url = "https://www.imdb.com/search/title/?groups=top_1000&view=simple&sort=user_rating,desc&count=100"
    for i in range(0, 901, 100):
        url = main_url + next_page_url(i) if i > 0 else main_url
        if validators.url(url):
            info = get_film_info_from_page(url)
            if info:
                top_list += info
    return top_list


def main():
    """
    This produces 2 output csv files:
    File 1: A list of the top 1000 movies on IMDB
    File 2: A summary by year of the number of movies in IMDB and the number of movies in the Top 1000
    """
    film_counts = []
    film_list = get_top_film_list()
    if film_list:
        export_top_film_list(film_list)
        film_counts = get_total_film_counts()
        if film_counts:
            counter = 1
            for film in film_list:
                year = int(film.film_year)
                if year in film_counts:
                    film_counts[year].top_film_count += 1
                    film_counts[year].top_film_rating_total += film.get_rating_value()
                    film_counts[year].rating_values_list.append(film.get_rating_value())
                    film_counts[year].top_10_count += 1 if counter <= 10 else 0
                    film_counts[year].top_20_count += 1 if counter <= 20 else 0
                    film_counts[year].top_50_count += 1 if counter <= 50 else 0
                    film_counts[year].top_100_count += 1 if counter <= 100 else 0
                    film_counts[year].top_250_count += 1 if counter <= 250 else 0
                    film_counts[year].top_500_count += 1 if counter <= 500 else 0
                counter += 1
    if film_counts:
        export_aggregation_summary(film_counts)


if __name__ == '__main__':
    main()
