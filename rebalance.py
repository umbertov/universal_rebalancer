from time import sleep, time, ctime
import requests as R
from os import environ as env
from pandas import DataFrame
from binance import Client
from web3 import Web3

if "BINANCE_KEY" in env and "BINANCE_SECRET" in env:
    binance = Client(env["BINANCE_KEY"], env["BINANCE_SECRET"])
else:
    from getpass import getpass

    binance = Client(getpass("Binance API key: "), getpass("Binance API secret: "))


METAMASK_ADDRESS = "0x57D09090dD2b531b4ed6e9c125f52B9651851Afd"
ARBI_RPC = "https://arb1.arbitrum.io/rpc"
arbi = Web3(Web3.HTTPProvider(ARBI_RPC))


def get_metamask_eth_balance():
    bal_wei = arbi.eth.getBalance(METAMASK_ADDRESS)
    bal_eth = arbi.fromWei(bal_wei, "ether")
    return float(bal_eth)


BTC_ADDRESS = "bc1qkp4mydvu4f62kgfkxyw85g94j5lt568h6aq627"
BALANCE_URL = "https://blockchain.info/q/addressbalance/" + BTC_ADDRESS

BALANCES: dict[str, float] = {"BTC": 0.0, "BUSD": 0, "ETH": 0}
BALANCES_USD: dict[str, float] = {"BTC": 0, "ETH": 0, "BUSD": 0.0}

TOLERANCE = 0.02


CONSTRAINTS = {
    "BTC/BUSD": {
        "ratio": 3 / 2,
        "over": lambda: binance.create_test_order(
            symbol=f"BTCBUSD",
            quantity=0.0008,
            side=binance.SIDE_SELL,
            type=binance.ORDER_TYPE_MARKET,
        ),
        "under": lambda: binance.create_test_order(
            symbol=f"BTCBUSD",
            quantity=0.0008,
            side=binance.SIDE_BUY,
            type=binance.ORDER_TYPE_MARKET,
        ),
    },
    "BTC/ETH": {
        "ratio": 3 / 2,
        "over": lambda: binance.create_test_order(
            symbol=f"ETHBTC",
            quantity=0.013,
            side=binance.SIDE_BUY,
            type=binance.ORDER_TYPE_MARKET,
        ),
        "under": lambda: binance.create_test_order(
            symbol=f"ETHBTC",
            quantity=0.013,
            side=binance.SIDE_SELL,
            type=binance.ORDER_TYPE_MARKET,
        ),
    },
}


def check_constraints(constraints: dict[str, dict], balances: dict[str, float]):
    for key, thing in constraints.items():
        ratio = thing["ratio"]
        coin1, coin2 = key.split("/")
        actual_ratio = balances[coin1] / balances[coin2]
        # print(f"{key} current ratio: {actual_ratio:.2f}, target: {ratio:.2f}", end="\t")
        if actual_ratio > ratio * (1 + TOLERANCE):
            pass
            # print(f"should sell {coin1} into {coin2}")
            # print(thing["over"]())
        elif actual_ratio < ratio * (1 - TOLERANCE):
            pass
            # print(f"should buy {coin1} using {coin2}")
            # print(thing["under"]())
        else:
            pass
            # print(" all is going good.")
        # print(f"\t Upper ratio: {ratio * (1+TOLERANCE):.3f}")
        # print(f"\t Lower ratio: {ratio * (1-TOLERANCE):.3f}")


def sat_to_btc(x):
    return x * 1e-8


print(
    "date",
    "time_secs",
    "btc_balance",
    "btc_value",
    "eth_balance",
    "eth_value",
    "usd_balance",
    sep=",",
)

while True:
    cold_btc_balance = sat_to_btc(float(R.get(BALANCE_URL).text))
    binance_btc = binance.get_asset_balance("BTC")
    hot_btc_balance = float(binance_btc["free"]) + float(binance_btc["locked"])
    BALANCES["BTC"] = cold_btc_balance + hot_btc_balance

    binance_busd = binance.get_asset_balance("BUSD")
    BALANCES["BUSD"] = float(binance_busd["free"]) + float(binance_busd["locked"])

    binance_eth = binance.get_asset_balance("ETH")
    BALANCES["ETH"] = float(binance_eth["free"]) + float(binance_eth["locked"])
    metamask_eth = get_metamask_eth_balance()
    BALANCES["ETH"] += metamask_eth

    tickers = DataFrame(binance.get_all_tickers()).set_index("symbol").astype(float)

    btc_price = tickers.loc["BTCBUSD"].item()
    BALANCES_USD["BTC"] = btc_price * BALANCES["BTC"]

    eth_price = tickers.loc["ETHBUSD"].item()
    BALANCES_USD["ETH"] = eth_price * BALANCES["ETH"]

    BALANCES_USD["BUSD"] = BALANCES["BUSD"]

    # print(BALANCES_USD)
    date, time_secs = ctime(), time()
    print(
        date,
        time_secs,
        BALANCES["BTC"],
        BALANCES_USD["BTC"],
        BALANCES["ETH"],
        BALANCES_USD["ETH"],
        BALANCES["BUSD"],
        sep=",",
    )

    check_constraints(CONSTRAINTS, BALANCES_USD)

    sleep(5)
