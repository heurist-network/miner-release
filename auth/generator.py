import os
import sys
import json
import toml
import time
from web3 import Web3
from mnemonic import Mnemonic
from dotenv import load_dotenv
from prettytable import PrettyTable
from eth_account.messages import encode_defunct

class WalletGenerator:
    def __init__(self, config_file, abi_file):
        load_dotenv()
        
        with open(config_file, 'r') as file:
            config = toml.load(file)
            rpc_url = config['contract']['rpc']
            contract_address = config['contract']['address']
            self.keys_dir = os.path.expanduser(config['storage']['keys_dir'])
                
        with open(abi_file, 'r') as file:
            contract_abi = json.load(file)
        
        os.makedirs(self.keys_dir, exist_ok=True)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract = self.w3.eth.contract(address=contract_address, abi=contract_abi)

    def print_table(self, data):
        table = PrettyTable()
        table.field_names = ["Key", "Value"]
        table.align["Key"] = "l"
        table.align["Value"] = "l"
        for key, value in data.items():
            table.add_row([key, value])
        print(table)
        print("Make sure you back up the identity wallet file. One identity wallet is bound to one miner address receiving rewards. The identity wallet is used for authentication only. DO NOT deposit funds into the identity wallet.\n")

    def fetch_iw_address(self, rw_address):
        return self.contract.functions.identityAddress(Web3.to_checksum_address(rw_address)).call()

    def is_bind(self, rw_address):
        return '0x0000000000000000000000000000000000000000' != self.fetch_iw_address(rw_address)

    def read_wallet_file(self, file_path):
        with open(file_path, 'r') as file:
            seed_phrase = file.readline().strip().split(': ')[1]
            iw_address = file.readline().strip().split(': ')[1]
        return seed_phrase, iw_address

    def write_wallet_file(self, file_path, seed_phrase, iw_address):
        with open(file_path, 'w') as file:
            file.write(f"Seed Phrase: {seed_phrase}\n")
            file.write(f"Identity Wallet Address: {iw_address.lower()}\n")  # Store identity wallet address in lowercase

    def generate_wallets(self):
        for key, value in os.environ.items():
            if key.startswith('MINER_ID_'):
                miner_id = value
                rw_address = miner_id.split('-')[0].lower()  # Extract the address
                file_path = os.path.join(self.keys_dir, f'{miner_id.lower()}.txt')

                if not self.is_bind(rw_address):
                    # Case: There's no binding
                    if os.path.exists(file_path):
                        # Check if the [RW].txt file exists
                        seed_phrase, iw_address = self.read_wallet_file(file_path)
                        print(f"\033[1mMiner ID: {miner_id}\033[0m - Warning: Identity wallet file for Reward Wallet {rw_address} is found, but binding is not established on-chain.")
                    else:
                        print(f"\033[1mMiner ID: {miner_id}\033[0m - No binding identity wallet, generating one...")
                        mnemo = Mnemonic("english")
                        seed_phrase = mnemo.generate(strength=128)
                        self.w3.eth.account.enable_unaudited_hdwallet_features()
                        account = self.w3.eth.account.from_mnemonic(seed_phrase)
                        iw_address = account.address
                        self.write_wallet_file(file_path, seed_phrase, iw_address)

                else:
                    # Case: There is a binding
                    if not os.path.exists(file_path):
                        # We don't have the RW.txt file
                        print(f"\033[1mMiner ID: {miner_id}\033[0m - Binding identity wallet found yet text file missing...")
                        print("Please import the seed phrase for the Identity Wallet.")
                        seed_phrase = input("Seed Phrase: ")
                        self.w3.eth.account.enable_unaudited_hdwallet_features()
                        account = self.w3.eth.account.from_mnemonic(seed_phrase)
                        imported_iw_address = account.address

                        bind_iw_address = self.fetch_iw_address(rw_address)
                        while imported_iw_address.lower() != bind_iw_address.lower():  # Compare in lowercase
                            print("Imported Identity Wallet address does not match the bind address.")
                            print("Please try again with the correct seed phrase.")
                            seed_phrase = input("Seed Phrase: ")
                            account = self.w3.eth.account.from_mnemonic(seed_phrase)
                            imported_iw_address = account.address

                        self.write_wallet_file(file_path, seed_phrase, imported_iw_address)

                    else:
                        # We have the RW.txt file
                        print(f"\033[1mMiner ID: {miner_id}\033[0m - Binding identity wallet found")
                        seed_phrase, iw_address = self.read_wallet_file(file_path)

                        bind_iw_address = self.fetch_iw_address(rw_address)
                        if iw_address.lower() != bind_iw_address.lower():  # Compare in lowercase
                            raise ValueError(f"Mismatch found for Miner ID {miner_id}.")
                        
                seed_phrase, iw_address = self.read_wallet_file(file_path)
                data = {
                    "Miner ID": miner_id,
                    "Identity Wallet Seed Phrase": seed_phrase,
                    "Identity Wallet Address": iw_address,
                    "Wallet File": file_path
                }
                self.print_table(data)

    def validate_miner_keys(self, miner_ids):
        # miner_id may be composite address, e.g., miner_id = 0x1234-GPUNAME"
        for miner_id in miner_ids:
            reward_wallet = miner_id.split('-')[0].lower()  # Extract the address
            file_path = os.path.join(self.keys_dir, f'{reward_wallet}.txt')

            if not os.path.exists(file_path):
                print(f"ERROR: Identity wallet file missing for Reward Wallet {reward_wallet}. Exiting...")
                raise ValueError(f"Identity wallet file not found in ~/.heurist-keys for Reward Wallet {reward_wallet}. Run `python3 auth/generator.py` to generate the identity wallet.")

            seed_phrase, iw_address = self.read_wallet_file(file_path)

            if not self.is_bind(reward_wallet):
                print(f"Warning: Identity wallet binding is not established for Reward Wallet {reward_wallet}. The binding will be effective after completion of some compute jobs.")
            else:
                bind_iw_address = self.fetch_iw_address(reward_wallet)
                if iw_address.lower() != bind_iw_address.lower():
                    print(f"ERROR: Identity wallet mismatch found for Reward Wallet {reward_wallet}. Exiting...")
                    raise ValueError(f"Identity wallet mismatch found for Reward Wallet {reward_wallet}.")

            print(f"MINER ID {miner_id} authenticated. Proceed to mining.")

    def generate_signature(self, miner_id):
        reward_wallet = miner_id.split('-')[0].lower()  # Extract the address
        file_path = os.path.join(self.keys_dir, f'{reward_wallet}.txt')
        seed_phrase, iw_address = self.read_wallet_file(file_path)
        
        self.w3.eth.account.enable_unaudited_hdwallet_features()
        private_key = self.w3.eth.account.from_mnemonic(seed_phrase).key
        
        current_time_secs = int(time.time())
        hourly_time = current_time_secs - (current_time_secs % 3600)  # Unix Timestamp Round down to the nearest hour
        
        message = f"{reward_wallet}-{hourly_time}" # Always lower case
        signable_message = encode_defunct(text=message)
        signature = self.w3.eth.account.sign_message(signable_message, private_key=private_key)
        
        return iw_address.lower(), signature.signature.hex()

if __name__ == '__main__':
    abi_file = os.path.join(os.path.dirname(__file__), 'abi.json')
    config_file = os.path.join(os.path.dirname(__file__), '..', 'config.toml')
    wallet_generator = WalletGenerator(config_file, abi_file)
    wallet_generator.generate_wallets()
