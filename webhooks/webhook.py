import json
import time
from mcrealms.mcrclient import MCRealmsClient
import requests
import os
from dotenv import load_dotenv

load_dotenv()
USERNAME = os.environ['USERNAME']
EMAIL = os.environ['EMAIL']
PASSWORD = os.environ['PASSWORD']
SERVER_ID = int(os.environ['SERVER_ID'])
DISCORD_WEBHOOKS_URL = os.environ['DISCORD_WEBHOOKS_URL']


def main():
    realmsClient = MCRealmsClient(USERNAME, EMAIL, PASSWORD)

    prevPlayers = set(realmsClient.getPlayersList(SERVER_ID))

    while True:
        activePlayerNames = realmsClient.getPlayersList(SERVER_ID)
        currPlayers = set(activePlayerNames)
        newlyOnlinePlayers = currPlayers.difference(prevPlayers)
        print(prevPlayers, currPlayers, newlyOnlinePlayers)
        prevPlayers = currPlayers

        for playerName in newlyOnlinePlayers:
            headers = {"Content-Type": 'application/json'}
            body = {
                'content': f'@everyone {playerName} is now playing on the server!'
            }
            requests.post(url=DISCORD_WEBHOOKS_URL,
                          data=json.dumps(body), headers=headers)

        time.sleep(60)


if __name__ == '__main__':
    main()
