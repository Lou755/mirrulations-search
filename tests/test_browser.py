import time
import json
import subprocess
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options

@pytest.fixture(name="driver")
def fixture_driver():

     # Start Flask app
    process = subprocess.Popen(
    ["flask", "--app", "src.mirrsearch.app", "run", "--port", "5001", "--no-reload"]
    )

    # Give server time to start
    time.sleep(5)
    
    # Needed to work with Github CI
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    set_up_driver = webdriver.Chrome(options=options)

    set_up_driver.get('http://127.0.0.1:5001')

    # This allows the test to run, and then clean up the driver and process after
    yield set_up_driver

    set_up_driver.quit()
    process.terminate()

def test_browser_search(driver):

    search_terms = ['test', 'esrd']

    for search_term in search_terms:
        driver.find_element(By.ID, 'searchInput').clear()
        driver.find_element(By.ID, 'searchInput').send_keys(search_term)

        driver.find_element(By.ID, 'searchButton').click()

        output = driver.find_element(By.ID, 'output')

        wait = WebDriverWait(driver, timeout=10)
        wait.until(lambda d: d.find_element(By.ID, 'output').text != "")

        if search_term not in ['esrd']:
            expected = []
        else:
            expected = [
        {
            "agency_id": "CMS",
            "cfrPart": "42 CFR Parts 413 and 512",
            "docket_id": "CMS-2025-0240",
            "document_type": "Proposed Rule",
            "title": (
                "CY 2026 Changes to the End-Stage Renal Disease (ESRD) "
                "Prospective Payment System and Quality Incentive Program. "
                "CMS1830-P Display"
            ),
        }
    ]

        assert json.loads(output.text) == expected
