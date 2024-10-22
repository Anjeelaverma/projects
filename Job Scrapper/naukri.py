import httpx
import asyncio
import csv
import re
import os
from datetime import datetime
import time
import random
from colorama import Fore
from tqdm import tqdm

max_concurrent_requests = 4
min_delay_between_requests = 1
max_delay_between_requests = 3
timeout_duration = 10

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]

def clean_html(raw_html):
    if raw_html is None:
        return ""
    clean_text = re.sub(r'<.*?>', '', raw_html)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    clean_text = re.sub(r'(amp;)+', '', clean_text)
    return clean_text.strip()

main_url = 'https://www.naukri.com'

async def fetch(client, url, headers):
    try:
        response = await client.get(url, headers=headers, timeout=timeout_duration)
        if response.status_code != 200:
            raise httpx.HTTPStatusError(f"Unexpected status code: {response.status_code}", request=response.request, response=response)
        return response.json()
    except Exception as e:
        print(Fore.RED + f"{url}: {e}", Fore.RESET)
        raise

async def fetch_allJob_json(client, url):
    headers = {
        "accept": "application/json",
        "appid": "103",
        "cache-control": "no-cache",
        "clientid": "d3skt0p",
        "content-type": "application/json",
        "priority": "u=1, i",
        "referer": "https://www.naukri.com/it-companies-in-india-cat116?src=gnbCompanies_homepage_srch&title=IT%20Companies%20Hiring",
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "systemid": "js",
        "user-agent": random.choice(user_agents)
    }
    return await fetch(client, url, headers)

async def fetch_eachComp_json(client, url, job_url):
    headers_each_company = {
        "accept": "application/json",
        "appid": "109",
        "cache-control": "no-cache",
        "clientid": "d3skt0p",
        "content-type": "application/json",
        "priority": "u=1, i",
        "referer": job_url,
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "systemid": "109",
        "user-agent": random.choice(user_agents)
    }
    return await fetch(client, url, headers_each_company)

async def fetch_eachJob_json(client, url, jd_url):
    headers_job = {
        "accept": "application/json",
        "appid": "121",
        "clientid": "d3skt0p",
        "content-type": "application/json",
        "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
        "priority": "u=1, i",
        "referer": jd_url,
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "systemid": "Naukri",
        "user-agent": random.choice(user_agents)
    }
    return await fetch(client, url, headers_job)

async def get_job_urls():
    async with httpx.AsyncClient(http2=True, limits=httpx.Limits(max_keepalive_connections=32, max_connections=25)) as client:
        url = 'https://www.naukri.com/companyapi/v1/search?seoKey=/it-companies-in-india-cat116&category_id=116&urltype=search_by_category_id&pageNo=1&qcount=48&searchType=companySearch'
        resp = await fetch_allJob_json(client, url)
        total = resp.get('noOfGroups')
        print(Fore.YELLOW + f'Total', Fore.CYAN + f'{total}', Fore.YELLOW + 'Companies Found.')

        url = f'https://www.naukri.com/companyapi/v1/search?seoKey=/it-companies-in-india-cat116&category_id=116&urltype=search_by_category_id&pageNo=1&qcount={total}&searchType=companySearch'
        resp = await fetch_allJob_json(client, url)
        group_details = resp.get('groupDetails', [])
        job_urls = []

        for group in group_details:
            group_jobs_url = group.get("groupJobsURL")
            if group_jobs_url is not None and '?' in group_jobs_url:
                job_urls.append(main_url + group_jobs_url)

        print(Fore.YELLOW + f'Total', Fore.GREEN + f'{len(job_urls)}', Fore.YELLOW + 'Valid Data Found.', Fore.RESET)
        return job_urls

async def get_jobs(job_url, client, semaphore, writer, progress):
    async with semaphore:
        comp_id = re.findall(r'overview-(.*?)\?', job_url)[0]
        each_comp_url = f'https://www.naukri.com/jobapi/v3/search?noOfResults=20&groupId={comp_id}&pageNo=1&searchType=groupidsearch'
        each_company_res = await fetch_eachComp_json(client, each_comp_url, job_url)
        total_jobs = each_company_res.get('noOfJobs', 0)

        extracted_data = []
        results_per_page = 100
        total_pages = (total_jobs // results_per_page) + (1 if total_jobs % results_per_page > 0 else 0)

        for page in range(1, total_pages + 1):
            each_comp_url = f'https://www.naukri.com/jobapi/v3/search?noOfResults={results_per_page}&groupId={comp_id}&pageNo={page}&searchType=groupidsearch'
            each_company_res = await fetch_eachComp_json(client, each_comp_url, job_url)
            job_details = each_company_res.get('jobDetails', [])

            for job in job_details:
                jd_url = job.get("jdURL")
                if jd_url:
                    jd_url = main_url + jd_url
                else:
                    continue

                company_name = clean_html(job.get('companyName'))
                title = job.get('title')
                skills = job.get("tagsAndSkills")
                job_description = clean_html(job.get("jobDescription"))
                experience = next((item.get("label") for item in job.get("placeholders", []) if item.get("type") == "experience"), '')
                location = next((item.get("label") for item in job.get("placeholders", []) if item.get("type") == "location"), '')
                ambition_data = job.get("ambitionBoxData", {})
                reviews_count = ambition_data.get("ReviewsCount")
                aggregate_rating = ambition_data.get("AggregateRating")
                jd_id = jd_url.split('-')[-1]
                job_url_T = f'https://www.naukri.com/jobapi/v4/job/{jd_id}?microsite=y'
                job_resp = await fetch_eachJob_json(client, job_url_T, jd_url)

                details = job_resp.get('jobDetails')
                if details:
                    education = details.get("education", {})
                    ug_education = education.get("ug")
                    ppg_education = education.get("ppg")
                    pg_education = education.get("pg")
                    required_education = f"UG: {ug_education[0] if ug_education else 'Not Required'} PG: {pg_education[0] if pg_education else 'Not Required'} PPG: {ppg_education[0] if ppg_education else 'Not Required'}"
                    salary = details.get("salaryDetail", {}).get("label")

                    job_data = {
                        "Company Name": company_name,
                        "Job Title": title,
                        "Job Location": location,
                        "Experience Required": experience,
                        "Skills Required": skills,
                        "Job Description": job_description,
                        "Total Reviews": reviews_count,
                        "Company Rating": aggregate_rating,
                        "Education Required": required_education,
                        "Salary": salary,
                    }
                    extracted_data.append(job_data)
                else:
                    job_data = {
                        "Company Name": company_name,
                        "Job Title": title,
                        "Job Location": location,
                        "Experience Required": experience,
                        "Skills Required": skills,
                        "Job Description": job_description,
                        "Total Reviews": reviews_count,
                        "Company Rating": aggregate_rating,
                        "Education Required": 'N/A',
                        "Salary": "N/A",
                    }
                    extracted_data.append(job_data)
         
                if extracted_data:
                    writer.writerow(job_data)
            progress.update(1)
            await asyncio.sleep(random.uniform(min_delay_between_requests, max_delay_between_requests))
        return extracted_data

def cleanup_csv(file_name):
    seen = set()
    temp_file = file_name + ".tmp"

    try:
        with open(file_name, 'r', encoding='utf-8') as infile, \
                open(temp_file, 'w', newline='', encoding='utf-8') as outfile:

            reader = csv.reader(infile)
            writer = csv.writer(outfile)

            for row in reader:
                row_tuple = tuple(row)
                if row_tuple not in seen:
                    writer.writerow(row)
                    seen.add(row_tuple)

        os.remove(file_name)
        os.rename(temp_file, file_name)
        print(Fore.GREEN + "Cleaned successfully." + Fore.RESET)

    except FileNotFoundError:
        print(Fore.RED + f"File {file_name} not found during cleanup." + Fore.RESET)
    except Exception as e:
        print(Fore.RED + f"An error occurred during cleanup: {e}" + Fore.RESET)


async def main():
    start_time = time.time()
    csv_name = f'Naukri_{datetime.now().strftime("%#d%b_%H-%M")}.csv'
    csv_columns = [
        "Company Name", "Job Title", "Job Location", "Experience Required",
        "Skills Required", "Job Description", "Total Reviews", "Company Rating",
        "Education Required", "Salary"
    ]

    try:
        job_urls = await get_job_urls()
        if not job_urls:
            print(Fore.RED + "No job URLs found. Exiting...", Fore.RESET)
            cleanup_csv(csv_name)
            return

        semaphore = asyncio.Semaphore(max_concurrent_requests)

        async with httpx.AsyncClient(http2=True) as client:
            with open(csv_name, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                writer.writeheader()

                with tqdm(total=len(job_urls), desc=Fore.LIGHTCYAN_EX + "Kaam Chal rha hai Bro/Sis" + Fore.RESET, colour="green") as progress:
                    tasks = [get_jobs(url, client, semaphore, writer, progress) for url in job_urls]
                    await asyncio.gather(*tasks)
    except Exception as e:
        print(Fore.RED + f"An error occurred: {e}", Fore.RESET)
        cleanup_csv(csv_name)
    finally:
        cleanup_csv(csv_name)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print('Time taken:', Fore.LIGHTMAGENTA_EX + f'{elapsed_time:.2f}s', Fore.RESET)

if __name__ == '__main__':
    asyncio.run(main())
