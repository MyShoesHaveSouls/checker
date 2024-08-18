import os
import configparser
import time
import datetime
import requests
from hdwallet import BIP44HDWallet
from hdwallet.cryptocurrencies import EthereumMainnet
from hdwallet.derivations import BIP44Derivation
from hdwallet.utils import generate_mnemonic
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure requests session with retries
session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

def check_connection():
    url = 'https://www.google.com/'
    try:
        session.get(url, timeout=10)
        return True
    except requests.RequestException:
        return False

def mainnet_url(mainnet):
    urls = {
        "bsc": "https://api.bscscan.com/",
        "eth": "https://api.etherscan.io/",
        "polygon": "https://api.polygonscan.com/"
    }
    return urls.get(mainnet, "https://api.bscscan.com/")

def mainnet_api(mainnet):
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config['api'].get(mainnet, '')

def req_trnx(mainnet, address):
    mainnet_url_link = mainnet_url(mainnet)
    mainnet_api_key = mainnet_api(mainnet)
    url = f"{mainnet_url_link}api?module=account&action=txlist&address={address}&apikey={mainnet_api_key}"
    try:
        response = session.get(url, timeout=30)
        return response.json()
    except requests.RequestException:
        return {"status": "0"}

def req_balance(mainnet, address):
    mainnet_url_link = mainnet_url(mainnet)
    mainnet_api_key = mainnet_api(mainnet)
    url = f"{mainnet_url_link}api?module=account&action=balance&address={address}&apikey={mainnet_api_key}"
    try:
        response = session.get(url, timeout=30)
        return response.json()
    except requests.RequestException:
        return {"result": "0"}

def process_wallet(address, mnemonic):
    check_mainnet = ['bsc', 'eth', 'polygon']
    results = {'trnxFound': 0, 'balanceFound': 0}

    def process_mainnet(mainnet):
        nonlocal results
        wallet_trnx_status = req_trnx(mainnet, address)
        if wallet_trnx_status.get("status") == "1":
            results['trnxFound'] += 1
            wallet_trnx_balance = req_balance(mainnet, address)
            if wallet_trnx_balance.get("result") != "0":
                results['balanceFound'] += 1
        return results

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_mainnet, mainnet) for mainnet in check_mainnet]
        for future in as_completed(futures):
            results.update(future.result())

    return results

def main():
    os.system('cls')
    hasTransactionPath = "hasTransaction"
    hasBalancePath = "hasBalance"
    todays_date = datetime.date.today()
    looper_count = 0
    init_run_time = time.monotonic()

    while True:
        start_time = time.monotonic()
        print(f"Total Checked: {looper_count}")

        MNEMONIC = generate_mnemonic(language="english", strength=128)
        bip44_hdwallet = BIP44HDWallet(cryptocurrency=EthereumMainnet)
        bip44_hdwallet.from_mnemonic(mnemonic=MNEMONIC)

        results = process_wallet(bip44_hdwallet.address(), bip44_hdwallet.mnemonic())

        if results['trnxFound']:
            with open(f"{hasTransactionPath}/hasTransaction-{todays_date}.txt", "a") as file:
                file.write(f" - || Mnemonic : {bip44_hdwallet.mnemonic()} || {bip44_hdwallet.address()}\n")

        if results['balanceFound']:
            with open(f"{hasBalancePath}/hasBalance-{todays_date}.txt", "a") as file:
                file.write(f" - {results['balanceFound']} || Mnemonic : {bip44_hdwallet.mnemonic()} || {bip44_hdwallet.address()}\n")

        looper_count += 1
        end_time = time.monotonic()
        execution_time = datetime.timedelta(seconds=end_time - start_time)
        run_time = datetime.timedelta(seconds=end_time - init_run_time)
        print(f"Execution Time: {execution_time} || Elapsed Time: {run_time}")

        # Clean derivation indexes/paths
        bip44_hdwallet.clean_derivation()
        os.system('cls')

if __name__ == '__main__':
    main()
