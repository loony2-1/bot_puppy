import requests # сходить на сайт и скачать страницу
from bs4 import BeautifulSoup #превращает HTML сайта в удобную структуру
import time

global_cache = {}   # кеш результатов поиска
city_cache = {}     # кеш данных ОДНОЙ ссылки (город + порода)
cache_time = {}     # время жизни кеша
CACHE_TTL = 600


def get_ad_data(link):
    if link in city_cache:
        return city_cache[link]

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(link, headers=headers, timeout=5)

        if response.status_code != 200:
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")

        city = None
        breed = None

        # 🔥 ищем ВСЕ строки с параметрами (более стабильно)
        for item in soup.find_all(["span", "li", "div", "p"]):

            text = item.get_text(" ", strip=True)

            # ---- ПОРOДА ----
            if "Порода" in text:
                breed_text = text.replace("Порода:", "").strip().lower()

                breed = breed_text.lower().strip()

            # ---- ГОРОД ----
            if "Место" in text:
                city_text = text.replace("Место:", "").strip()

                if "минск" in city_text.lower():
                    city = "Минск"
                elif "гомель" in city_text.lower():
                    city = "Гомель"
                elif "брест" in city_text.lower():
                    city = "Брест"

        city_cache[link] = (city, breed)

        if len(city_cache) > 500:
            city_cache.clear()

        return city, breed

    except Exception as e:
        print("Ошибка парсинга:", e)
        return None, None


def search_puppies(keyword, city):
    url = "https://www.doska.by/animals/dogs/"  # адрес сайта, который мы будем “парсить”

    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers) #ответ от сайта


    if response.status_code != 200:
        print("Ошибка загрузки")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser") #response.text → это HTML (огромный текст) BeautifulSoup превращает его в “дерево”

    results = [] #сюда будем складывать ссылки

    links = soup.select("a[href*='.html']")  # берём все ссылки

    for a in links:
        title = " ".join(a.text.split()).strip()
        link = a.get("href")

        # пропускаем пустые значения
        if not title or not link:
            continue

        # убираем мусорные заголовки
        if len(title) < 10:
            continue

        # ссылка
        if link.startswith("/"):
            link = "https://www.doska.by" + link
        elif not link.startswith("http"):
            link = "https://www.doska.by/" + link


        ad_city, ad_breed = get_ad_data(link)
        #print(ad_city, ad_breed)
        # фильтр по городу
        if city and (not ad_city or ad_city.lower() != city.lower()):
            continue

        # фильтр по породе
        if not ad_breed or keyword.lower() not in ad_breed.lower():
            continue

        results.append((title, link))
    return results

def search_puppies_smart(breed, city):
    key = (breed.lower(), city.lower() if city else None)
    now = time.time()

    if key in global_cache:
        if now - cache_time.get(key, 0) < CACHE_TTL:
            return global_cache[key]

    try:
        results = search_puppies(breed, city)
    except Exception as e:
        print("Search error:", e)
        return []

    global_cache[key] = results
    cache_time[key] = now

    return results
