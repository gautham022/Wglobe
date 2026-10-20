import httpx
import pycountry

async def get_country_details(country_code: str):
    country = pycountry.countries.get(alpha_2=country_code)
    full_name = country.name if country else country_code

    calling_code = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://restcountries.com/v3.1/alpha/{country_code}")
            if resp.status_code == 200:
                data = resp.json()[0]
                root = data["idd"]["root"]
                suffix = data["idd"]["suffixes"][0]
                calling_code = root + suffix
    except Exception:
        calling_code = None

    return full_name, calling_code