import requests
import csv
import time
from bs4 import BeautifulSoup
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
def check_existing_jobs(title, company, date_created):
    if not os.path.exists('jobs.csv'):
        return False
    with open('jobs.csv', 'r', newline='', encoding='utf-8') as existing_csv:
        reader = csv.reader(existing_csv)
        for existing_job in reader:
            if existing_job[0] == title and existing_job[1] == company and existing_job[3] == date_created:
                return True
    return False


# Extrair informações de uma vaga
def extract_job_information(job_element):
    title = job_element.find('h3', class_='base-search-card__title').text.strip()
    company = job_element.find('h4', class_='base-search-card__subtitle').text.strip()
    location = job_element.find('span', class_='job-search-card__location').text.strip()

    date_element = job_element.find('time', class_='job-search-card__listdate--new')
    date_created = date_element['datetime'] if date_element else ''

    url_element = job_element.find('a', class_='base-card__full-link')
    url = url_element['href'] if url_element else ''

    return title, company, location, date_created, url


# Função principal para raspagem
def scrape_linkedin_jobs(url, names_exception, names_remove, max_pages=2):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    page_number = 0
    total_results = 0

    proxies = {
        #"http": "http://209.121.164.51:31147",
        "http": "http://67.43.227.226:30255"
    }

    while page_number < max_pages * 25:  # Cada página tem 25 resultados
        try:
            response = requests.get(f'{url}={page_number}', headers=headers, proxies=proxies)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao fazer a requisição HTTP: {e}")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        results_container = soup.find('ul', class_='jobs-search__results-list')

        if not results_container:
            logger.info("Nenhum resultado encontrado na página atual.")
            break

        job_elements = results_container.find_all('div', class_='base-card')

        for job_element in job_elements:
            title, company, location, date_created, url = extract_job_information(job_element)

            if any(exp in title for exp in names_exception) and not any(name in title for name in names_remove):
                if not check_existing_jobs(title, company, date_created):
                    job_info = [title, company, location, date_created, url]
                    with open('jobs.csv', 'a', newline='', encoding='utf-8') as csv_file:
                        writer = csv.writer(csv_file)
                        writer.writerow(job_info)
                        total_results += 1

                    message = f"Título: {title}\nEmpresa: {company}\nLocalização: {location}\nData de Criação: {date_created}\nLink: {url}"
                    asyncio.run(send_telegram_message(message))

        logger.info(f"Página {page_number // 25 + 1}: {len(job_elements)} vagas processadas.")
        page_number += 25
        time.sleep(20)  # Pausa de 20 segundos entre as requisições

    logger.info(f"Foram extraídos {total_results} empregos e salvos no arquivo jobs.csv.")


if __name__ == '__main__':
    # Criar o arquivo CSV se ele não existir
    if not os.path.exists('jobs.csv'):
        with open('jobs.csv', 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Título", "Empresa", "Localização", "Data de Criação", "Link"])

    # Palavras-chave para filtrar vagas
    names_remove = {'Business', 'Cybersecurity', 'Technical', 'Salesforce', 'Data', 'Fullstack', 'Finance'}

    # URLs de pesquisa e filtros associados
    url_job_mapping = {
        # Remote, systems analyst, Canada
        'https://www.linkedin.com/jobs/search/?currentJobId=3540986533&f_TPR=r86400&f_WT=2&geoId=101174742&keywords=systems%20analyst&location=Canada&refresh=true&start':
            {'names_list': ['Systems', 'Support', 'Analyst']},
        # Remote, help desk, Canada
        'https://www.linkedin.com/jobs/search?keywords=Help%20Desk&location=Canada&geoId=101174742&f_TPR=r86400&f_WT=2&position=1&pageNum=0':
            {'names_list': ['']},
        # help desk, Vancouver
        #'https://www.linkedin.com/jobs/search/?currentJobId=4100084747&f_TPR=r86400&geoId=103366113&keywords=systems%20analyst&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true':
        #    {'names_list': ['']},
        # Outsystems, Canada
        'https://www.linkedin.com/jobs/search?keywords=Outsystems&location=Canada&locationId=&geoId=101174742&f_TPR=r604800&position=1&pageNum=0':
            {'names_list': ['OutSystems', 'Outsystems']},
        # Remote, Python developer, Canada
        'https://www.linkedin.com/jobs/search?keywords=Python%20Developer&location=Canada&locationId=&geoId=101174742&f_TPR=r86400&f_WT=2&position=1&pageNum=0&start':
            {'names_list': ['Python', 'Backend']},
        # Outsystems, Brazil, Remote
        'https://www.linkedin.com/jobs/search?keywords=Outsystems&location=Brazil&geoId=106057199&f_TPR=r604800&f_WT=2&position=1&pageNum=0':
            {'names_list': ['OutSystems', 'Outsystems']},
    }

    # Executar a raspagem para cada URL
    for url, config in url_job_mapping.items():
        scrape_linkedin_jobs(url, config['names_list'], names_remove)
