import time
import httpx
import re
import csv
import asyncio
import random
from datetime import datetime
from colorama import Fore

url = 'https://internshala.com/jobs/'
max_concurrent_requests = 12
min_delay_between_requests = 1  
max_delay_between_requests = 3

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]
async def get_total_pages():
    async with httpx.AsyncClient(http2=True, limits=httpx.Limits(max_keepalive_connections=32, max_connections=25)) as client:
        main_response = await client.get(url)
        return int(re.findall(r'total_pages\">(.*?)<', main_response.text)[0])

async def fetch_page(client, page_no):
    page_url = f'https://internshala.com/jobs/page-{page_no}/'
    response = await client.get(page_url)
    return response

async def get_data(semaphore, page_no, resp, failed_links, all_combined_data):
    company_intern_lnk = re.findall(r"data-href='(.*?)'", resp.text)
    company_intern_lnks = ['https://internshala.com' + i for i in company_intern_lnk]

    print(Fore.GREEN+'Getting data from page', Fore.LIGHTMAGENTA_EX+f"{page_no}",Fore.RESET)
    async with httpx.AsyncClient(http2=True, limits=httpx.Limits(max_keepalive_connections=32, max_connections=25)) as client:
        tasks = []
        for link in company_intern_lnks:
            tasks.append(fetch_company_data(semaphore, client, link, failed_links, all_combined_data))

        results = await asyncio.gather(*tasks)

        job_title = re.findall(r'job-title-href.*?blank\".(.*?)<', resp.text)
        company_name = re.findall(r'company-name\">\n(.*?)<', resp.text)
        company_name = [company.strip() for company in company_name]
        job_experience = re.findall(r'ic-16-briefcase.*\n.*?>(.*?)<', resp.text)
        job_money = re.findall(r'ic-16-money.*\n.*\n(.*?)<', resp.text)
        job_money = [money.strip() for money in job_money]

        for i in range(len(job_title)):
            try:
                company_data = results[i] if i < len(results) else ([], [], '', [])
                skills_required, opening, company_lnk, about_company = company_data
                all_combined_data.append([
                    job_title[i],
                    company_name[i],
                    company_lnk[0] if company_lnk else '',
                    job_experience[i] if i < len(job_experience) else '',
                    job_money[i] if i < len(job_money) else '',
                    skills_required if skills_required else [],
                    opening[0] if opening else '',
                    ' '.join(about_company) if about_company else ''
                ])
            except IndexError:
                print(Fore.RED+f"Index error while processing page{page_no} for job index {i}", Fore.RESET)

async def fetch_company_data(semaphore, client, url, failed_links, all_combined_data):
    async with semaphore:
        for attempt in range(7):  
            try:
                response = await client.get(url, headers={'User-Agent': random.choice(user_agents)})
                if response.status_code == 200:
                    skills_required = re.findall(r'<span class=\"round_tabs\">([^<]+)<\/span>', response.text)
                    opening = re.findall(r'Number of openings<\/h3>\s*<div class="text-container">\s*(\d+)\s*<\/div>', response.text)
                    company_lnk = re.findall(r"text-container website_link.*\n.*?='(.*?)'", response.text)
                    about_company = re.findall(r'text body-main\">(.*?)<', response.text)
                    return skills_required, opening, company_lnk, about_company
                elif response.status_code in (302, 429):
                    print("Received",Fore.YELLOW+f"{response.status_code}",Fore.RESET+ "for",Fore.CYAN+f"{url}",Fore.RESET+"retrying...")
                    await asyncio.sleep(random.uniform(min_delay_between_requests, max_delay_between_requests))
                else:
                    print("Error fetching",Fore.YELLOW+url,Fore.RESET+":", Fore.YELLOW+response.status_code, Fore.RESET)
                    failed_links.append(url)  
                    return [], [], '', []
            except httpx.RequestError as e:
                print(f"Request error for",Fore.CYAN+f"{url}",Fore.RESET,"retrying...")
                await asyncio.sleep(random.uniform(min_delay_between_requests, max_delay_between_requests))
        failed_links.append(url)
        return [], [], '', []

async def main():
    start_time = time.time()

    total_pages = await get_total_pages()
    start = input(f'Enter Page no. you want to start data from (total found pages are {total_pages}): ').split(' ')
    required_pages = []

    for i in start:
        if '-' not in i:
            required_pages.append(int(i))
        else:
            start_range, end_range = map(int, i.split('-'))
            required_pages.extend(range(start_range, end_range + 1))

    all_pages = sorted(list(set(required_pages)))
    failed_links = []  
    all_combined_data = []  

    semaphore = asyncio.Semaphore(max_concurrent_requests)
    async with httpx.AsyncClient(http2=True, limits=httpx.Limits(max_keepalive_connections=32, max_connections=25)) as client:
        tasks = []
        for page_no in all_pages:
            resp = await fetch_page(client, page_no)
            tasks.append(get_data(semaphore, page_no, resp, failed_links, all_combined_data))
        await asyncio.gather(*tasks)

    combined_filename = f'{datetime.now().strftime("%#d%b_%H-%M")}_Data.csv'
    

    with open(combined_filename, mode='w', newline='', encoding='utf-8') as combined_file:
        writer = csv.writer(combined_file)
        writer.writerow(['Job', 'Company', 'Company Link', 'Experience Required', 
                         'Salary', 'Skill(s) Required', 'Total Openings', 'Activity on Internshala'])
        for row in all_combined_data:
            writer.writerow(row)

    end_time = time.time()  
    elapsed_time = end_time - start_time
    print('Time taken:',Fore.GREEN+f'{elapsed_time:.2f} seconds', Fore.RESET)  

if __name__ == '__main__':
    asyncio.run(main())
