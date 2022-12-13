import asyncio
import traceback
import sys
from time import sleep, time, ctime
from typing import Any
import pandas
import requests as R
from os import environ as env
from pathlib import Path
from pandas import DataFrame

# from binance import Client
from web3 import Web3
import ccxt

from plotly.subplots import make_subplots
import plotly.graph_objects as go

from telegram_chart_bot import (
    get_bot as get_telegram_bot,
    send_latest_chart,
    telegram_notify_action,
)

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


DRY_RUN = False
CHECK_INTERVAL_SECONDS = 60

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

TOLERANCE = 0.05


CONSTRAINTS = {
    "BTC": {
        "ratio": 0.55,
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
    "ETH": {
        "ratio": 0.15,
        "overAction": dict(
            symbol=f"ETH/BUSD",
            amount=0.013,
            side="sell",
            type="market",
        ),
        "underAction": dict(
            symbol=f"ETH/BUSD",
            amount=0.013,
            side="buy",
            type="market",
        ),
    },
}


LAST_TRADES = {
        'BTC': 0.,
        'ETH': 0.,
}

def check_constraints(
    constraints: dict[str, dict], balances_usd: dict[str, float]
) -> dict[str, dict[str, Any]]:

    result = dict()
    total_usd = sum(balances_usd.values())

    for coin, thing in constraints.items():

        ratio = thing["ratio"]

        actual_ratio = balances_usd[coin] / total_usd

        upper_ratio = ratio * (1 + TOLERANCE)
        lower_ratio = ratio * (1 - TOLERANCE)

        print(
            f"{coin} current ratio: {actual_ratio:.2f}, target: between {lower_ratio:.3f} and {upper_ratio:.3f}",
            file=sys.stderr,
        )

        if actual_ratio > upper_ratio:
            action = thing["overAction"]
        elif actual_ratio < lower_ratio:
            action = thing["underAction"]
        else:
            action = dict()
        result[coin] = action
    return result


def perform_actions(exchange, actions):
    res = []
    for key, params in actions.items():
        print(ctime(), key, end="\n\t", file=sys.stderr)
        print(*params.items(), sep="\n\t", file=sys.stderr)
        if params and not DRY_RUN:
            symbol, side = params['symbol'], params['side']
            coin, quote = symbol.split("/")

            ohlcv = DataFrame(exchange.fetch_ohlcv(symbol, timeframe='1m'))
            close = ohlcv[4]
            mean = close.rolling(200).mean()
            ratio = close / mean - 1

            now = time()
            if side == 'buy' and ratio.iloc[-1] < -0.002:
                if now - LAST_TRADES[coin] > (4*60*60): # 4 hours
                    order = exchange.create_order(**params)
                    LAST_TRADES[coin] = now
                    asyncio.run(telegram_notify_action(params))
                    res.append(order)

            elif side == 'sell' and ratio.iloc[-1] > 0.002:
                if now - LAST_TRADES[coin] > (4*60*60): # 4 hours
                    order = exchange.create_order(**params)
                    LAST_TRADES[coin] = now
                    asyncio.run(telegram_notify_action(params))
                    res.append(order)
            else:
                print(f"not sending action because ratio is {ratio.iloc[-1]}", file=sys.stderr)

    return res


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

    maybe_send_chart()

    perform_actions(exchange, actions)

    sleep(CHECK_INTERVAL_SECONDS)


def maybe_send_chart():
    chart_path = Path("latest_chart.jpg")
    if not chart_path.exists():
        make_chart()
        return asyncio.run(send_latest_chart())

    mtime = chart_path.stat().st_mtime
    if time() - mtime > (60 * 60):  # 1 hour
        make_chart()
        return asyncio.run(send_latest_chart())


def make_chart():
    data: DataFrame = pandas.read_csv("balance_log.csv")
    invalid_positions = data.time_secs.str.endswith("time_secs")
    data = data[~invalid_positions].set_index("time_secs").drop("date", axis="columns")
    data.index = pandas.to_datetime(data.index, unit="s")
    data = data.astype(float)

    data = data.iloc[-500000:].ffill().resample("1h").agg("last")

    total_usd = data.btc_value + data.usd_balance + data.eth_value
    btc_pct = data.btc_value / total_usd
    eth_pct = data.eth_value / total_usd

    ############### ALLOCATION PCT TIME SERIES
    fig = make_subplots(
        rows=2, cols=1, subplot_titles=("BTC alloc pct", "ETH alloc pct")
    )

    fig.add_trace(go.Scatter(x=btc_pct.index, y=btc_pct), row=1, col=1)
    fig.add_hline(
        CONSTRAINTS["BTC"]["ratio"] * (1 + TOLERANCE),
        line_dash="dash",
        opacity=0.5,row=1,col=1
    )
    fig.add_hline(CONSTRAINTS["BTC"]["ratio"], opacity=0.5, row=1,col=1)
    fig.add_hline(
        CONSTRAINTS["BTC"]["ratio"] * (1 - TOLERANCE),
        line_dash="dash",
        opacity=0.5,row=1,col=1
    )

    fig.add_trace(go.Scatter(x=eth_pct.index, y=eth_pct), row=2, col=1)
    fig.add_hline(
        CONSTRAINTS["ETH"]["ratio"] * (1 + TOLERANCE), line_dash="dash", opacity=0.5,row=2,col=1
    )
    fig.add_hline(CONSTRAINTS["ETH"]["ratio"], opacity=0.5, row=2,col=1)
    fig.add_hline(
        CONSTRAINTS["ETH"]["ratio"] * (1 - TOLERANCE), line_dash="dash", opacity=0.5,row=2,col=1
    )

    fig.write_image("latest_chart.jpg", width="800", height="1000")

    ############### ASSET USD VALUE TIME SERIES
    portfolio_value = data[["btc_value", "eth_value", "usd_balance"]].sum(
        axis="columns"
    )

    fig = make_subplots(rows=2, cols=1, subplot_titles=("Assets value", "Total value"))

    fig.add_trace(go.Scatter(x=portfolio_value.index, y=portfolio_value), row=2, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=data.btc_value), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data.eth_value), row=1, col=1)

    fig.write_image("latest_value_chart.jpg", width="800", height="1000")

    ############### ALLOCATION PIE CHART
    fig = go.Figure(go.Pie(labels=list(BALANCES_USD.keys()), values=list(BALANCES_USD.values())))
    fig.update_layout(title="Allocation Pie Chart")
    fig.write_image("latest_pie_chart.jpg", width="1000", height="1000")



while True:
    try:
        exchange_loop(binance)
    except Exception as e:
        print(f"{ctime()} ERROR:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("..................................................", file=sys.stderr)
        sleep(CHECK_INTERVAL_SECONDS)
        print(ctime(), "resuming", file=sys.stderr)
