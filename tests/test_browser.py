import time
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

def test_browser_search():

    # Start Flask app
    process = subprocess.Popen(
    ["flask", "--app", "src.mirrsearch.app", "run", "--port", "5001", "--no-reload"]
    )

    # Give server time to start
    time.sleep(5)

    driver = webdriver.Chrome()
    driver.get('http://127.0.0.1:5001')

    search_input = driver.find_element(By.ID, 'searchInput')
    search_terms = ['test', 'esrd']

    for search_term in search_terms:
        search_input.clear()
        search_input.send_keys(search_term)

        driver.find_element(By.ID, 'searchButton').click()

        output = driver.find_element(By.ID, 'output')

        wait = WebDriverWait(driver, timeout=10)
        wait.until(lambda d: d.find_element(By.ID, 'output').text != "")

        if search_term not in ['esrd']:
            expected = '''[]'''
        else:
            expected = '''[{"agency_id":"CMS",
            "cfrPart":"42 CFR Parts 413 and 512",
            "docket_id":"CMS-2025-0240",
            "document_type":"Proposed Rule",
            "title":"CY 2026 Changes to the End-Stage Renal Disease 
            (ESRD) Prospective Payment System and Quality Incentive Program. 
            CMS1830-P Display"}]'''

        assert output.text == expected

    driver.quit()
    process.terminate()
