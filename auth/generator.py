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
        self.keys_dir = os.path.expanduser('~/.heurist-keys')
        os.makedirs(self.keys_dir, exist_ok=True)
        
        with open(config_file, 'r') as file:
            config = toml.load(file)
            rpc_url = config['contract']['rpc']
            contract_address = config['contract']['address']
        
        with open(abi_file, 'r') as file:
            contract_abi = json.load(file)
        
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

    def is_bind(self, rw_address):
        return self.contract.functions.identityAddress(rw_address).call() != '0x0000000000000000000000000000000000000000'

    def generate_wallets(self):
        for key, value in os.environ.items():
            if key.startswith('MINER_ID_'):
                miner_id = value
                rw_address = miner_id  # Use miner_id as the reward wallet address
                file_path = os.path.join(self.keys_dir, f'{miner_id.lower()}.txt')

                if not self.is_bind(rw_address):
                    # Case: There's no binding
                    print(f"\033[1mMiner ID: {miner_id}\033[0m - No binding identity wallet, generating one...")
                    mnemo = Mnemonic("english")
                    seed_phrase = mnemo.generate(strength=128)
                    self.w3.eth.account.enable_unaudited_hdwallet_features()
                    account = self.w3.eth.account.from_mnemonic(seed_phrase)
                    iw_address = account.address

                    with open(file_path, 'w') as file:
                        file.write(f"Seed Phrase: {seed_phrase}\n")
                        file.write(f"Identity Key: {iw_address.lower()}\n")  # Store identity wallet address in lowercase

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

                        bind_iw_address = self.contract.functions.identityAddress(rw_address).call()
                        while imported_iw_address.lower() != bind_iw_address.lower():  # Compare in lowercase
                            print("Imported Identity Wallet address does not match the bind address.")
                            print("Please try again with the correct seed phrase.")
                            seed_phrase = input("Seed Phrase: ")
                            account = self.w3.eth.account.from_mnemonic(seed_phrase)
                            imported_iw_address = account.address

                        with open(file_path, 'w') as file:
                            file.write(f"Seed Phrase: {seed_phrase}\n")
                            file.write(f"Identity Key: {imported_iw_address.lower()}\n")  # Store identity wallet address in lowercase

                    else:
                        # We have the RW.txt file
                        print(f"\033[1mMiner ID: {miner_id}\033[0m - Binding identity wallet found and text file located, printing to console...")
                        with open(file_path, 'r') as file:
                            seed_phrase = file.readline().strip().split(': ')[1]
                            iw_address = file.readline().strip().split(': ')[1]

                        bind_iw_address = self.contract.functions.identityAddress(rw_address).call()
                        if iw_address.lower() != bind_iw_address.lower():  # Compare in lowercase
                            print(f"Mismatch found for Miner ID {miner_id}. Aborting.")
                            return
                        
                with open(file_path, 'r') as file:
                    seed_phrase = file.readline().strip().split(': ')[1]
                    iw_address = file.readline().strip().split(': ')[1]
                data = {
                    "Miner ID": miner_id,
                    "Seed Phrase": seed_phrase,
                    "Identity Wallet": iw_address,
                    "Wallet File": file_path
                }
                self.print_table(data)
    
    def validate_miner_keys(self, miner_ids):
        for miner_id in miner_ids:
            file_path = os.path.join(self.keys_dir, f'{miner_id.lower()}.txt')

            if not os.path.exists(file_path):
                print(f"ERROR: Text file missing for Miner ID {miner_id}. Exiting...")
                raise ValueError(f"Text file missing for Miner ID {miner_id}.")

            with open(file_path, 'r') as file:
                seed_phrase = file.readline().strip().split(': ')[1]
                iw_address = file.readline().strip().split(': ')[1]

            if not self.is_bind(miner_id):
                print(f"WARNING: Identity file exists but no binding found for Miner ID {miner_id}. Proceeding with caution...")
            else:
                bind_iw_address = self.contract.functions.identityAddress(miner_id).call()
                if iw_address.lower() != bind_iw_address.lower():
                    print(f"ERROR: Mismatch found for Miner ID {miner_id}. Exiting...")
                    raise ValueError(f"Mismatch found for Miner ID {miner_id}.")

            print(f"MINER ID {miner_id} validated. Proceed to mining loop...")

    def generate_signature(self, miner_id):
        file_path = os.path.join(self.keys_dir, f'{miner_id.split("-")[0].lower()}.txt')
        with open(file_path, 'r') as file:
            seed_phrase = file.readline().strip().split(': ')[1]
        
        self.w3.eth.account.enable_unaudited_hdwallet_features()
        private_key = self.w3.eth.account.from_mnemonic(seed_phrase).key
        
        current_time_secs = int(time.time())
        hourly_time = current_time_secs - (current_time_secs % 3600)  # Unix Timestamp Round down to the nearest hour
        
        message = f"{miner_id.split('-')[0].lower()}-{hourly_time}"
        signable_message = encode_defunct(text=message)
        signature = self.w3.eth.account.sign_message(signable_message, private_key=private_key)
        
        return signature.signature.hex()

if __name__ == '__main__':
    abi_file = abi_file = os.path.join(os.path.dirname(__file__), 'abi.json')
    config_file = os.path.join(os.path.dirname(__file__), '..', 'config.toml')
    wallet_generator = WalletGenerator(config_file, abi_file)
    wallet_generator.generate_wallets()