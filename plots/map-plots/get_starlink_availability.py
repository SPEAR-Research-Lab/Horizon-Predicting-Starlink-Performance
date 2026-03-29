"""
This sources Starlink availability data by scraping their order page
using Selenium, and saves the list of countries to a CSV file.
"""

from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://starlink.com/order?processorToken=4c98f067-39c6-4136-9e76-f65097dacf36&step=0"
data_dir = Path(__file__).parent / "data"


def get_starlink_countries() -> list[str]:
    ChromeDriverManager().install()
    driver = webdriver.Chrome(options=webdriver.ChromeOptions())

    driver.get(URL)
    wait = WebDriverWait(driver, 15)

    try:
        cookie_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        cookie_btn.click()
        print("Cookie banner dismissed")
    except:
        print("No cookie banner detected, continuing...")

    country_selector = wait.until(
        EC.presence_of_element_located((By.ID, "country-selector"))
    )
    country_selector.click()

    ul_element = wait.until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "ul[role='listbox'].MuiList-root.MuiList-padding.MuiMenu-list",
            )
        )
    )

    li_elements = ul_element.find_elements(By.TAG_NAME, "li")
    countries = [
        li.get_attribute("data-value")
        for li in li_elements
        if li.get_attribute("data-value")
    ]

    driver.quit()
    return countries


def save_countries_to_file() -> None:
    countries = get_starlink_countries()
    countries_df = pd.DataFrame(countries, columns=["country_code"])
    output_file = data_dir / "starlink_countries.csv"
    countries_df.to_csv(output_file, index=False)


if __name__ == "__main__":
    save_countries_to_file()
