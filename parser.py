import aiohttp
import asyncio
import time
from bs4 import BeautifulSoup

global_cache = {}
city_cache = {}
cache_time = {}
CACHE_TTL = 600


# ---------------- FETCH ----------------
async def fetch(session, url): #скачивает HTML страницы
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers, timeout=5) as response: #максимум 5 секунд ожидания
            if response.status != 200:
                return None
            return await response.text() #получаем HTML страницы
    except:
        return None


# ---------------- GET AD DATA ----------------
async def get_ad_data(session, link):
    if link in city_cache: #если уже парсили — не идём в интернет
        return city_cache[link]

    html = await fetch(session, link) #Скачиваем страницу
    if not html:
        return None, None

    soup = BeautifulSoup(html, "html.parser") #Парсим HTML

    city = None
    breed = None

    for item in soup.find_all(["span", "li", "div", "p"]): #Ищем данные
        text = item.get_text(" ", strip=True)

        if "Порода" in text:
            breed = text.replace("Порода:", "").strip().lower()

        if "Место" in text:
            city_text = text.replace("Место:", "").strip().lower()

            if "минск" in city_text:
                city = "Минск"
            elif "гомель" in city_text:
                city = "Гомель"
            elif "брест" in city_text:
                city = "Брест"

    city_cache[link] = (city, breed) #Сохраняем в кеш

    if len(city_cache) > 500:
        city_cache.clear()

    return city, breed


# ---------------- MAIN SEARCH ----------------
async def search_puppies(keyword, city):
    url = "https://www.doska.by/animals/dogs/"

    async with aiohttp.ClientSession() as session: #один клиент на все запросы (важно для скорости)
        html = await fetch(session, url) #Получаем страницу со списком объявлений

        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("a[href*='.html']") #берём все ссылки на объявления

        tasks = [] #список async задач
        prepared = [] #хранит (title, link)

        for a in links:
            title = " ".join(a.text.split()).strip()
            link = a.get("href")

            if not title or not link:
                continue

            if len(title) < 10:
                continue

            if link.startswith("/"):
                link = "https://www.doska.by" + link
            elif not link.startswith("http"):
                link = "https://www.doska.by/" + link

            prepared.append((title, link))
            tasks.append(get_ad_data(session, link)) #Заполняем задачи

        results_data = await asyncio.gather(*tasks) #запускает ВСЕ запросы одновременно

        results = []

        for (title, link), (ad_city, ad_breed) in zip(prepared, results_data): #Обработка результатов

            # фильтр по городу
            if city and (not ad_city or ad_city.lower() != city.lower()):
                continue

            # фильтр по породе
            if not ad_breed or keyword.lower() not in ad_breed.lower():
                continue

            results.append((title, link))

        return results


# ---------------- SMART CACHE ----------------
async def search_puppies_smart(breed, city):
    key = (breed.lower(), city.lower() if city else None) #Ключ кеша
    now = time.time()

    if key in global_cache:
        if now - cache_time.get(key, 0) < CACHE_TTL: #если прошло меньше 10 минут — возвращаем кеш
            return global_cache[key]

    try:
        results = await search_puppies(breed, city)
    except Exception as e:
        print("Search error:", e)
        return []

    global_cache[key] = results
    cache_time[key] = now

    return results