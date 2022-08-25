import os

class Auth: 
    def __init__(self):
        self.API_KEY = os.getenv('ALPACA_KEY')
        self.API_SECRET = os.getenv('ALPACA_SECRET')
        self.BASE_URL = os.getenv('BASE_URL')
        