import asyncio
import aiohttp
import pandas as pd
from sys import stderr
from loguru import logger
from aptos_sdk.account import Account

api_2captcha = 'c7ea5d00906cbc40447a00e13488ea9e'

logger.remove()
logger.add(stderr,
           format="<lm>{time:HH:mm:ss}</lm> | <level>{level}</level> | <blue>{function}:{line}</blue> "
                  "| <lw>{message}</lw>")
site_key = '0f30e95a-3d8a-4d78-8658-07e4c5ae38b2'


class Movement:
    def __init__(self, private_key: str, proxy: str, number_acc: int) -> None:
        self.private_key = private_key.strip()
        self.proxy: str = f"http://{proxy}" if proxy is not None else None
        self.id: int = number_acc
        self.client = None
        if self.private_key.startswith("0x"):
            self.private_key = self.private_key[2:]

    async def pre_claim(self) -> None:
        async with aiohttp.ClientSession(headers={
            'authority': 'auth.privy.io',
            'accept': 'application/json',
            'accept-language': 'en-GB,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://airdrop.shardeum.org',
            'privy-app-id': 'cm74a120m008j2flaznivfoa4',
            'privy-ca-id': '73ab7018-5ab7-4834-b739-d51c49959b83',
            'privy-client': 'react-auth:1.99.1',
            'referer': 'https://airdrop.shardeum.org/',
            'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/130.0.0.0 Safari/537.36',
        }) as client:
            self.client = client

            response: aiohttp.ClientResponse = await self.client.get(
                f'https://claims.movementnetwork.xyz/api/get-nonce',
                proxy=self.proxy,
            )
            response_json: dict = await response.json()
            nonce = response_json['nonce']

            acc = Account.load_key(self.private_key)

            message = f"APTOS\nmessage: Please sign this message to confirm ownership. Nonce: {nonce}\nnonce: {nonce}"
            signature = str(acc.sign(message.encode()))[2:]
            captcha_url = f"http://2captcha.com/in.php?key={api_2captcha}&method=hcaptcha&sitekey={site_key}&" \
                          f"pageurl=https://claims.movementnetwork.xyz/preclaim"
            response = await self.client.get(captcha_url, proxy=self.proxy)
            response_text = await response.text()
            if response_text.startswith("OK"):
                captcha_id = response_text.split("|")[1]
                for _ in range(20):
                    await asyncio.sleep(10)
                    result_url = f"http://2captcha.com/res.php?key={api_2captcha}&action=get&id={captcha_id}"
                    result_response = await self.client.get(result_url, proxy=self.proxy)
                    result_response_text = await result_response.text()
                    if 'OK' in result_response_text:
                        token = result_response_text.split('|')[1]
                        json_data = {
                            'address': str(acc.address()),
                            'message': message,
                            'signature': signature,
                            'publicKey': str(acc.public_key()),
                            'nonce': nonce,
                            'token': token,
                        }
                        response: aiohttp.ClientResponse = await self.client.post(
                            f'https://claims.movementnetwork.xyz/api/preclaim-reg',
                            json=json_data,
                            proxy=self.proxy,
                        )
                        response_json: dict = await response.json()
                        if response_json['success']:
                            logger.success(f"#{self.id} | {str(acc.address())} success registered | "
                                           f"{response_json['error']}")
                            return None
                logger.error(f"#{self.id} | {str(acc.address())} | captcha not solved")


async def start_follow(account: list, id_acc: int, semaphore) -> None:
    async with semaphore:
        acc = Movement(private_key=account[0], proxy=account[1],
                       number_acc=id_acc)

        try:

            await acc.pre_claim()

        except Exception as e:
            logger.error(f'ID account:{id_acc} Failed: {str(e)}')


async def main() -> None:
    semaphore: asyncio.Semaphore = asyncio.Semaphore(10)

    tasks: list[asyncio.Task] = [
        asyncio.create_task(coro=start_follow(account=account, id_acc=idx, semaphore=semaphore))
        for idx, account in enumerate(accounts, start=1)
    ]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    with open('accounts_data.xlsx', 'rb') as file:
        exel = pd.read_excel(file)
    accounts: list[list] = [
        [
            row["Private key"],
            row["Proxy"] if isinstance(row["Proxy"], str) else None
        ]
        for index, row in exel.iterrows()
    ]
    logger.info(f'My channel: https://t.me/CryptoMindYep')
    logger.info(f'Total wallets: {len(accounts)}\n')

    asyncio.run(main())

    logger.success('The work completed')
    logger.info('Thx for donat: 0x5AfFeb5fcD283816ab4e926F380F9D0CBBA04d0e')
