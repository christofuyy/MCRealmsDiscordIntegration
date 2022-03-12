import requests
import json
from ._mcauth import MCAuthenticator


class MCRealmsClient:
    """
    Client that consumes Minecraft Realms API

    Attributes
    ----------
    MC_REALMS_DOMAIN : str
        Domain of Minecraft API
    CLIENT_TOKEN : str
        Token used by auth server to generate access token.
        https://wiki.vg/Authentication#Authenticate
    """

    MC_REALMS_DOMAIN: str = 'https://pc.realms.minecraft.net'
    CLIENT_TOKEN: str = 'my-client-token'

    def __init__(self, username: str, email: str, password: str):
        """
        Inits client ready to consume Minecraft Realms API

        Parameters
        ----------
        username : str
            Username of Minecraft account
        email : str
            Email of Microsoft account
        password : str
            Password of Microsoft account
        """
        self._session = requests.Session()
        self._username = username
        accessToken, uid = self._authenticate(username, email, password)
        self._accessToken = accessToken
        self._uid = uid

    def getPlayersList(self, targetServerId: int) -> list[str]:
        """
        Returns list of names of players currently playing on the server with the given server ID

        Parameters
        ----------
        targetServerId : int
            ID of server to list active players from

        Returns
        -------
        playerNames : list[str]
            List of players current playing on the server
        """
        url = self.MC_REALMS_DOMAIN+'/activities/liveplayerlist'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Cookie': f'sid=token:{self._accessToken}:{self._uid};user={self._username};version=1.18.2'
        }
        res = self._session.get(url=url, headers=headers)
        resPayload = res.json()
        serverActivityList = resPayload['lists']
        for serverActivity in serverActivityList:
            serverId = serverActivity['serverId']
            if serverId != targetServerId:
                continue

            playerListStr = serverActivity['playerList']
            playerList = json.loads(playerListStr)
            return [self.getPlayerName(player['playerId']) for player in playerList]

        return []

    def getPlayerName(self, uid: int) -> str:
        """
        Returns the username of the player with the given uid

        Parameters
        ----------
        uid : int
            Id of the user to get the username for

        Returns
        -------
        username : str
            Username of user with given `uid`
        """
        return MCAuthenticator.getUsername(uid)

    def _authenticate(self, username: str, email: str, password: str) -> tuple[str, int]:
        """
        Authenticates with Minecraft and returns the access token and uid of authenticated user

        Parameters
        ----------
        username : str
            Username of user
        email : str
            Email of user to authenticate with Minecraft
        password : str
            Password of user to authenticate with Minecraft

        Returns
        -------
        accessToken : str
            Minecraft access token
        uid : int
            Uid of authenticated user
        """
        credentials = {'email': email, 'password': password}
        accessToken = MCAuthenticator.authenticate(self._session, credentials)
        uid = MCAuthenticator.getUid(username)

        return accessToken, uid
