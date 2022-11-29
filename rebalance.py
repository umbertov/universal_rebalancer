import traceback
import sys
from time import sleep, time, ctime
from typing import Any
import requests as R
from os import environ as env
from pandas import DataFrame

# from binance import Client
from web3 import Web3
import ccxt

if "BINANCE_KEY" in env and "BINANCE_SECRET" in env:
    # binance = Client(env["BINANCE_KEY"], env["BINANCE_SECRET"])
    binance = ccxt.binance(
        {"apiKey": env["BINANCE_KEY"], "secret": env["BINANCE_SECRET"]}
    )
else:
    from getpass import getpass

    binance = ccxt.binance(
        {
            "apiKey": getpass("Binance API key: "),
            "secret": getpass("Binance API secret: "),
        }
    )

DRY_RUN = True
CHECK_INTERVAL_SECONDS = 30

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

TOLERANCE = 0.1


CONSTRAINTS = {
    "BTC/BUSD": {
        "ratio": 3 / 2,
        "overAction": dict(
            symbol=f"BTC/BUSD",
            amount=0.0008,
            side="sell",
            type="market",
        ),
        "underAction": dict(
            symbol=f"BTC/BUSD",
            amount=0.0008,
            side="buy",
            type="market",
        ),
    },
    "BTC/ETH": {
        "ratio": 3 / 2,
        "overAction": dict(
            symbol=f"ETH/BTC",
            amount=0.013,
            side="buy",
            type="market",
        ),
        "underAction": dict(
            symbol=f"ETH/BTC",
            amount=0.013,
            side="sell",
            type="market",
        ),
    },
}


def check_constraints(
    constraints: dict[str, dict], balances: dict[str, float]
) -> dict[str, dict[str, Any]]:
    result = dict()
    for key, thing in constraints.items():

        ratio = thing["ratio"]
        coin1, coin2 = key.split("/")

        actual_ratio = balances[coin1] / balances[coin2]

        upper_ratio = ratio * (1 + TOLERANCE)
        lower_ratio = ratio * (1 - TOLERANCE)

        print(
            f"{key} current ratio: {actual_ratio:.2f}, target: between {lower_ratio:.3f} and {upper_ratio:.3f}",
            file=sys.stderr,
        )

        if actual_ratio > upper_ratio:
            action = thing["overAction"]
        elif actual_ratio < lower_ratio:
            action = thing["underAction"]
        else:
            action = lambda: None
        result[key] = action
    return result


def perform_actions(exchange, actions):
    for params in actions.values():
        if params:
            return exchange.create_order(params)


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


def exchange_loop(exchange):
    binance_balances = exchange.fetch_balance()

    cold_btc_balance = sat_to_btc(float(R.get(BALANCE_URL).text))
    binance_btc = binance_balances["BTC"]
    hot_btc_balance = float(binance_btc["total"])
    BALANCES["BTC"] = cold_btc_balance + hot_btc_balance

    binance_busd = binance_balances["BUSD"]
    BALANCES["BUSD"] = float(binance_busd["total"])

    binance_eth = binance_balances["ETH"]
    BALANCES["ETH"] = float(binance_eth["total"])
    metamask_eth = get_metamask_eth_balance()
    BALANCES["ETH"] += metamask_eth

    tickers = DataFrame(exchange.fetch_tickers().values()).set_index("symbol")

    btc_price = tickers.loc["BTC/BUSD", "last"].item()
    BALANCES_USD["BTC"] = btc_price * BALANCES["BTC"]

    eth_price = tickers.loc["ETH/BUSD", "last"].item()
    BALANCES_USD["ETH"] = eth_price * BALANCES["ETH"]

    BALANCES_USD["BUSD"] = BALANCES["BUSD"]

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

    actions = check_constraints(CONSTRAINTS, BALANCES_USD)

    if not DRY_RUN:
        perform_actions(exchange, actions)
    else:
        for key, action in actions.items():
            print(ctime(), key, end="\n\t", file=sys.stderr)
            print(*action.items(), sep="\n\t", file=sys.stderr)

    sleep(CHECK_INTERVAL_SECONDS)


while True:
    try:
        exchange_loop(binance)
    except Exception as e:
        print(f"{ctime()} ERROR:", file=sys.stderr)
        traceback.print_exception(e, file=sys.stderr)
        print("..................................................", file=sys.stderr)
        sleep(CHECK_INTERVAL_SECONDS)
        print(ctime(), "resuming", file=sys.stderr)
