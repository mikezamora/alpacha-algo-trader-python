from dotenv import load_dotenv
from crypto import Crypto

def main():
    load_dotenv()
    Crypto().start_algo()

if __name__ == "__main__":
    main()