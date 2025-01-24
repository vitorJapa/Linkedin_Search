from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import time
import random
import os
import logging
from telegram import Bot
import asyncio
from dotenv import load_dotenv, find_dotenv

# Carregar variáveis de ambiente
load_dotenv(find_dotenv())
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Configurar o logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('log.txt')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# Função para enviar mensagem no Telegram
async def send_telegram_message(message):
    bot = Bot(TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message)

# Função para verificar se a vaga já existe no arquivo CSV
def check_existing_jobs(title, company, location):
    if not os.path.exists('jobs.csv'):
        return False
    with open('jobs.csv', 'r', newline='', encoding='utf-8') as existing_csv:
        reader = csv.reader(existing_csv)
        for existing_job in reader:
            if existing_job[0] == title and existing_job[1] == company and existing_job[2] == location:
                return True
    return False

# Configurar o WebDriver
def configure_webdriver():
    service = Service('C:/Users/Vitor Kihara/Desktop/NodeProjects/teste/client/node_modules/chromedriver/lib/chromedriver/chromedriver.exe')  # Caminho para o chromedriver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# Função principal para raspagem
def scrape_indeed_jobs(url, keywords, max_pages=2):
    driver = configure_webdriver()
    total_results = 0

    try:
        for page in range(0, max_pages):
            logger.info(f"Acessando página {page + 1}")
            driver.get(f'{url}&start={page * 10}')

            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'tapItem'))
            )

            job_elements = driver.find_elements(By.CLASS_NAME, 'tapItem')

            for job_element in job_elements:
                try:
                    title_element = job_element.find_element(By.CLASS_NAME, 'jobTitle')
                    company_element = job_element.find_element(By.CLASS_NAME, 'companyName')
                    location_element = job_element.find_element(By.CLASS_NAME, 'companyLocation')
                    url_element = job_element.find_element(By.CLASS_NAME, 'jcs-JobTitle')

                    title = title_element.text.strip()
                    company = company_element.text.strip()
                    location = location_element.text.strip()
                    #url = f"https://ca.indeed.com{url_element.get_attribute('href')}"

                    if any(keyword.lower() in title.lower() for keyword in keywords):
                        if not check_existing_jobs(title, company, location):
                            job_info = [title, company, location, url]
                            with open('jobs.csv', 'a', newline='', encoding='utf-8') as csv_file:
                                writer = csv.writer(csv_file)
                                writer.writerow(job_info)
                                total_results += 1

                            message = f"Título: {title}\nEmpresa: {company}\nLocalização: {location}\nLink: {url}"
                            asyncio.run(send_telegram_message(message))

                except Exception as e:
                    logger.error(f"Erro ao processar uma vaga: {e}")

            logger.info(f"Página {page + 1}: {len(job_elements)} vagas processadas.")
            time.sleep(random.uniform(10, 20))

    except Exception as e:
        logger.error(f"Erro geral na raspagem: {e}")

    finally:
        driver.quit()

    logger.info(f"Foram extraídos {total_results} empregos e salvos no arquivo jobs.csv.")

if __name__ == '__main__':
    # Criar o arquivo CSV se ele não existir
    if not os.path.exists('jobs.csv'):
        with open('jobs.csv', 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Título", "Empresa", "Localização", "Link"])

    # URL base para busca de vagas no Indeed
    base_url = "https://ca.indeed.com/jobs?q=python+developer&l=Canada"

    # Palavras-chave para filtrar vagas
    keywords = ['Python', 'Developer', 'Backend']

    # Executar a raspagem
    scrape_indeed_jobs(base_url, keywords)
