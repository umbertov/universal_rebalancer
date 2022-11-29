from decimal import Decimal
from time import sleep, time, ctime
import json
from typing import Union

from web3 import Web3
from web3.eth import Address


METAMASK_ADDRESS = "0x57D09090dD2b531b4ed6e9c125f52B9651851Afd"

GLP_ADDRESS = Address("0x1aDDD80E6039594eE970E5872D247bf0414C8903")
SGLP_ABI = json.load(open("./abis/stakedGLP_ABI.json"))


class ClientFactory:
    URLS = {
        "arbitrum": "https://arb1.arbitrum.io/rpc",
    }

    @classmethod
    def arbitrum(cls):
        return cls.build("arbitrum")

    @classmethod
    def build(cls, name):
        return Web3(Web3.HTTPProvider(cls.URLS[name]))


def wei_to_eth(x: Union[int, Decimal]) -> float:
    return float(client.fromWei(float(x), "ether"))


def get_glp_price(client) -> float:
    aum = GlpManager.caller.getAum(False)
    total_supply = Glp.caller.totalSupply()
    return aum / total_supply / 10**12


def get_token_balance(token):
    bal_wei = token.caller.balanceOf(METAMASK_ADDRESS)
    return wei_to_eth(bal_wei)


if __name__ == "__main__":
    client = ClientFactory.arbitrum()
    glp = client.eth.contract(address=GLP_ADDRESS, abi=SGLP_ABI)

    GlpManager = client.eth.contract(
        address=Web3.toChecksumAddress("0x321f653eed006ad1c29d174e17d96351bde22649"),
        abi=json.load(open("./abis/GlpManager_ABI.json")),
    )
    Glp = client.eth.contract(
        address=Web3.toChecksumAddress("0x4277f8f2c384827b5273592ff7cebd9f2c1ac258"),
        abi=json.load(open("./abis/GLP_ABI.json")),
    )

    print("Value,Price,Amount")

    while True:
        glp_price = get_glp_price(client)
        glp_amt = get_token_balance(glp)
        glp_value = glp_price * glp_amt

        print(f"{glp_value:.2f},{glp_price},{glp_amt}")
        sleep(30)
