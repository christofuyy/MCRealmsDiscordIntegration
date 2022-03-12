"""Defines MCAuthenticator class
"""

import json
import re
import requests


class MCAuthenticator:
    """
    Static class that handles Minecraft authentication

    Attributes
    ----------
    MICROSOFT_AUTH_DOMAIN : str
        Domain of Microsoft authentication server
    XBOX_LIVE_AUTH_DOMAIN : str
        Domain of Xbox Live authentication server that authenticates users
    XBOX_LIVE_XSTS_AUTH_DOMAIN : str
        Domain of Xbox Live authentication server that provides XSTS tokens
    MINECRAFT_AUTH_DOMAIN : str
        Domain of Minecraft authentication server
    MOJANG_DOMAIN
        Domain of Minecraft API
    """

    MICROSOFT_AUTH_DOMAIN: str = 'https://login.live.com'
    XBOX_LIVE_AUTH_DOMAIN: str = 'https://user.auth.xboxlive.com'
    XBOX_LIVE_XSTS_AUTH_DOMAIN: str = 'https://xsts.auth.xboxlive.com'
    MINECRAFT_AUTH_DOMAIN: str = 'https://api.minecraftservices.com'
    MOJANG_DOMAIN: str = 'https://api.mojang.com'

    @staticmethod
    def getUsername(uid: int) -> str:
        """
        Gets profile names of Minecraft user from uid

        Parameters
        ----------
        uid : int
            Id of user to get profile name for

        Returns
        -------
        profileName : str
            Current profile name of user with given uid
        """
        url = MCAuthenticator.MOJANG_DOMAIN+f'/user/profiles/{uid}/names'
        res = requests.get(url=url)
        resPayload = res.json()
        currProfileName = resPayload[0]['name']
        return currProfileName

    @staticmethod
    def getUid(profileName: str) -> int:
        """
        Gets uid of Minecraft user from profile name

        Parameters
        ----------
        profileName : str
            Current profile name of desired user

        Returns
        -------
        uid : int
            Id of user with given `profileName`
        """
        url = MCAuthenticator.MOJANG_DOMAIN+'/users/profiles/minecraft/'+profileName
        headers = {
            "Accept": "application/json"
        }
        res = requests.get(url=url, headers=headers)
        resPayload = res.json()
        return resPayload['id']

    @staticmethod
    def authenticate(session: requests.Session, credentials: dict):
        """
        Authenticates the client for Minecraft

        Parameters
        ----------
        session : `requests.Session`
            Session of client to make HTTP requests with
        credentials : dict
            Dictionary with 'email' and 'password' keys and string values of the user email and password respectively

        Returns
        -------
        accessToken : str
            Access token used in Cookie header of authenticated requests
        """
        # TODO: move debug messages to corresponding methods
        sFTTag, urlPost = MCAuthenticator._prepareMicrosoftLogin(session)
        print('STATUS 200: Successfully prepared for authentication')
        msAccessToken = MCAuthenticator._authenticateWithMicrosoft(
            session, urlPost, sFTTag, credentials)
        print('STATUS 200: Authenticated with Microsoft')
        xboxLiveToken, userHash = MCAuthenticator._authenticateWithXboxLive(
            session, msAccessToken)
        print('STATUS 200: Authenticated with Xbox Live')
        xstsToken = MCAuthenticator._getXstsToken(session, xboxLiveToken)
        print('STATUS 200: Retrieved xsts token')
        mcAccessToken = MCAuthenticator._authenticateWithMinecraft(
            session, xstsToken, userHash)
        print('STATUS 200: Authenticated with Minecraft')
        return mcAccessToken

    @staticmethod
    def _prepareMicrosoftLogin(session: requests.Session) -> tuple[str, str]:
        """
        Gets sFTTag and url to make authentication request to

        Parameters
        ----------
        session : `requests.Session`
            Session of client to make HTTP requests with

        Returns
        -------
        sFTTag : str
            sFTTag required to authenticate with Microsoft
        urlPost : str
            Url to make POST request to authenticate with Microsoft
        """
        url = MCAuthenticator.MICROSOFT_AUTH_DOMAIN + \
            '/oauth20_authorize.srf?client_id=000000004C12AE6F&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en'
        res = session.get(url)

        match = re.search(r'value="(.+?)"', res.text)
        if not match:
            raise Exception(
                'SFTTagNotFoundError: sFTTag value was not found')

        sFTTagSource = match.group()
        sFTTag = sFTTagSource[sFTTagSource.index('\"')+1:-1]

        match = re.search(r"urlPost:'(.+?)'", res.text)
        if not match:
            raise Exception(
                'URLPostNotFoundError: url post value was not found')

        urlPostSource = match.group()
        urlPost = urlPostSource[urlPostSource.index('\'')+1:-1]

        return sFTTag, urlPost

    @staticmethod
    def _authenticateWithMicrosoft(session: requests.Session, authServerUrl: str, sFTTag: str, credentials: dict) -> str:
        """
        Authenticates with Microsoft and gets Microsoft access token

        Parameters
        ----------
        session : `requests.Session`
            Session of client to make HTTP requests with
        authServerUrl : str
            Url to make authentication request to
        sFTTag : str
            sFTTag required to authenticate with Microsoft
        credentials : dict
            Dictionary with 'email' and 'password' keys and string values of the user email and password respectively

        Returns
        -------
        accessToken : str
            Microsoft access token
        """
        email, password = credentials['email'], credentials['password']
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        body = f"login={email}&loginfmt={email}&passwd={password}&PPFT={sFTTag}"

        res = session.post(url=authServerUrl,
                           data=body, headers=headers)
        loginData = MCAuthenticator._getParamsFromUrl(res.url)
        return loginData['access_token']

    @staticmethod
    def _authenticateWithXboxLive(session: requests.Session, accessToken: str) -> tuple[str, str]:
        """
        Authenticates with Xbox Live and gets Xbox Live token and user hash

        Parameters
        ----------
        session : `requests.Session`
            Session of client to make HTTP requests with
        accessToken : str
            Microsoft access token
        """
        url = MCAuthenticator.XBOX_LIVE_AUTH_DOMAIN+'/user/authenticate'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        body = {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": accessToken
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT"
        }
        res = session.post(
            url=url, data=json.dumps(body), headers=headers)
        resPayload = res.json()
        xboxLiveToken = resPayload['Token']
        uhs = resPayload['DisplayClaims']['xui'][0]['uhs']
        return xboxLiveToken, uhs

    @staticmethod
    def _getXstsToken(session: requests.Session, xboxLiveToken: str) -> str:
        """
        Gets XSTS token from Xbox Live

        Parameters
        ----------
        session : `requests.Session`
            Session of client to make HTTP requests with
        xboxLiveToken : str
            Xbox Live token

        Returns
        -------
        xstsToken : str
            Xsts token required for Minecraft authentication
        """
        url = MCAuthenticator.XBOX_LIVE_XSTS_AUTH_DOMAIN+'/xsts/authorize'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        body = {
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [xboxLiveToken]
            },
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT"
        }
        res = session.post(
            url=url, data=json.dumps(body), headers=headers)
        resPayload = res.json()
        xstsToken = resPayload['Token']
        return xstsToken

    @staticmethod
    def _authenticateWithMinecraft(session: requests.Session, xstsToken: str, userHash: str) -> str:
        """
        Authenticates with Minecraft and returns Minecraft access token

        Parameters
        ----------
        session : `requests.Session`
            Session of client to make HTTP requests with
        xstsToken : str
            Xbox Live XSTS Token
        userHash : str
            Xbox Live user hash

        Returns
        -------
        accessToken : str
            Minecraft access token
        """
        url = MCAuthenticator.MINECRAFT_AUTH_DOMAIN+'/authentication/login_with_xbox'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        body = {
            "identityToken": f"XBL3.0 x={userHash};{xstsToken}",
            "ensureLegacyEnabled": True
        }
        res = session.post(
            url=url, data=json.dumps(body), headers=headers)
        resPayload = res.json()
        accessToken = resPayload['access_token']
        return accessToken

    @staticmethod
    def _getParamsFromUrl(url: str) -> dict:
        """
        Returns dict of the query parameters keys and values from the given url

        Parameters
        ----------
        url : str
            Url to extract query parameters from

        Returns
        -------
        params : dict
            Dict of query parameters keys and values of given url
        """
        allParamsStr = url.split('#')[1]
        paramsList = allParamsStr.split('&')
        params = {}
        for paramStr in paramsList:
            param, val = paramStr.split('=')
            params[param] = val
        return params
