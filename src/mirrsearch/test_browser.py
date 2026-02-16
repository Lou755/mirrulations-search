# Add selenium script
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
import dotenv
import os

dotenv.load_dotenv()
url = os.getenv('URL')
driver = webdriver.Chrome()
driver.get(url)

search_input = driver.find_element(By.ID, 'searchInput')
search_button = driver.find_element(By.ID, 'searchButton')
search_terms = ['test', 'Medicare']

for search_term in search_terms:
    search_input.clear()
    search_input.send_keys(search_term)

    search_button.click()

    output = driver.find_element(By.ID, 'output')

    wait = WebDriverWait(driver, timeout=10)
    wait.until(lambda d: d.find_element(By.ID, 'output').text != "")

    if search_term != 'Medicare':
        expected = '''[]'''
    else:
        expected = '''[{"agency_id":"CMS","cfrPart":"42 CFR Parts 413 and 512","docket_id":"CMS-2025-0240","document_type":"Proposed Rule","title":"Medicare Program: End-Stage Renal Disease Prospective Payment System, Payment for Renal Dialysis Services Furnished to Individuals with Acute Kidney Injury, End-Stage Renal Disease Quality Incentive Program, and End-Stage Renal Disease Treatment Choices Model"}]'''

    assert output.text == expected

driver.quit()
