# https://wallpaperscraft.com
import requests
import aiofiles
import asyncio
import aiohttp
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from get_symbols import symb_dict
from aiohttp_retry import RetryClient, ExponentialRetry
from aiohttp_socks import ChainProxyConnector, ProxyConnector

ua = UserAgent()
HEADERS = {
        'User-Agent': ua.random,
        'X-Requested-With': 'XMLHttpRequest'
    }
BASE_URL = 'https://wallpaperscraft.com'


def replace_chars(in_str):
    out_str = ''
    for char in in_str:
        if char in symb_dict:
            char = symb_dict[char]
        out_str += char
    return out_str


def collecting_image_pages(url):
    img_url_list = []
    response = requests.get(url=url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'lxml')
    wallpapers_list = soup.find('ul', class_='wallpapers__list').findAll('a', class_='wallpapers__link')
    for item in wallpapers_list:
        img_url_list.append(f'{BASE_URL}{item["href"]}')
    print('.', end='')
    return img_url_list


async def collecting_image_urls(session, page, image_url_list=[]):
    retry_options = ExponentialRetry(attempts=5)
    retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
                               start_timeout=0.5)
    async with retry_client.get(page) as response:
        soup = BeautifulSoup(await response.text(), 'lxml')
        image_href = soup.find('div', class_='wallpaper-table__row').find('a')['href']

        async with retry_client.get(f'{BASE_URL}{image_href}') as response_2:
            soup_2 = BeautifulSoup(await response_2.text(), 'lxml')
            image_url = soup_2.find('img', class_='wallpaper__image')['src']
            image_url_list.append(image_url)
            print('.', end='')


async def write_file(session, image_url, image_name):
    async with aiofiles.open(image_name, mode='wb') as f:
        async with session.get(image_url) as response:
            async for x in response.content.iter_chunked(1024):
                await f.write(x)
        print(f'Image is downloaded: {image_name}')


def url_to_name(image_url):
    image_name = image_url
    for counter in range(1, len(image_url)):
        char = image_url[len(image_url) - counter]
        if char == '/':
            image_name = image_url[len(image_url) - counter + 1:]
            break
    return image_name


async def main():
    search_str = 'anime'
    search_url = f'{BASE_URL}/search/?order=&page=10&query={replace_chars(search_str)}'
    print('Process:', end=' ')
    image_page_list = collecting_image_pages(search_url)

    # connector = ChainProxyConnector.from_urls(
    #     [
    #         'socks5://37.18.73.94:5566',
    #         'socks5://47.243.95.228:10080',
    #         'socks5://61.178.99.43:7302'
    #     ]
    # )

    connector = ProxyConnector.from_url('socks5://37.18.73.94:5566')

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        image_url_list = []
        tasks = []
        for page in image_page_list:
            task = asyncio.create_task(collecting_image_urls(session, page, image_url_list))
            tasks.append(task)
        await asyncio.gather(*tasks)
        print(' URL collecting is competed')

        tasks = []
        for image_url in image_url_list:
            image_name = f'wallpaper/{url_to_name(image_url)}'
            task = asyncio.create_task(write_file(session, image_url, image_name))
            tasks.append(task)
        await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
