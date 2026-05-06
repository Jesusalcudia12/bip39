import requests
from flask import Flask, jsonify
from mnemonic import Mnemonic
from bip_utils import (
    Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes,
    SolanaConf, Solana
)

app = Flask(__name__)

# --- FUNCIONES DE SALDO ---

def get_balance_btc(address):
    try:
        res = requests.get(f"https://blockchain.info/rawaddr/{address}", timeout=5)
        return res.json().get("final_balance", 0) / 100000000 if res.status_code == 200 else 0
    except: return 0

def get_balance_evm(address, rpc_url):
    """Sirve para ETH, BNB y Polygon"""
    try:
        payload = {
            "jsonrpc": "2.0", "method": "eth_getBalance",
            "params": [address, "latest"], "id": 1
        }
        res = requests.post(rpc_url, json=payload, timeout=5)
        hex_bal = res.json().get("result", "0x0")
        return int(hex_bal, 16) / 10**18
    except: return 0

def get_balance_sol(address):
    try:
        payload = {
            "jsonrpc": "2.0", "method": "getBalance",
            "params": [address], "id": 1
        }
        res = requests.post("https://api.mainnet-beta.solana.com", json=payload, timeout=5)
        return res.json().get("result", {}).get("value", 0) / 10**9
    except: return 0

@app.route('/api/generate', methods=['GET'])
def generate_all():
    try:
        # Generar Mnemónico
        mnemo = Mnemonic("english")
        words = mnemo.generate(strength=128)
        seed_bytes = Bip39SeedGenerator(words).Generate()

        # 1. BITCOIN (m/44'/0'/0'/0/0)
        btc_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
        btc_addr = btc_ctx.PublicKey().ToAddress()

        # 2. ETHEREUM / POLYGON / BNB (Misma dirección m/44'/60'/0'/0/0)
        eth_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
        evm_addr = eth_ctx.PublicKey().ToAddress()

        # 3. SOLANA (m/44'/501'/0'/0')
        sol_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
        sol_addr = sol_ctx.PublicKey().ToAddress()

        return jsonify({
            "status": "success",
            "mnemonic": words,
            "wallets": {
                "bitcoin": {"address": btc_addr, "balance": get_balance_btc(btc_addr), "symbol": "BTC"},
                "ethereum": {"address": evm_addr, "balance": get_balance_evm(evm_addr, "https://cloudflare-eth.com"), "symbol": "ETH"},
                "binance": {"address": evm_addr, "balance": get_balance_evm(evm_addr, "https://bsc-dataseed.binance.org/"), "symbol": "BNB"},
                "polygon": {"address": evm_addr, "balance": get_balance_evm(evm_addr, "https://polygon-rpc.com"), "symbol": "MATIC"},
                "solana": {"address": sol_addr, "balance": get_balance_sol(sol_addr), "symbol": "SOL"}
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def handler(event, context):
    return app(event, context)
