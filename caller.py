# imports
from bs4 import BeautifulSoup
import requests
import json
import asyncio
import pandas as pd

class Caller:
    
    def __init__(self, apiKey) -> None:
        self.apiKey = apiKey
        self.steamId = None
        self.steamName = 'Not Available'
        self.processedData = None
        return
    '''
    uses the callers apiKey to fetch a steam users game information in a human readable, processed manner,
    the steam user must have their account visibility set to 'public'
    '''
    async def getData(self, steamId) -> pd.core.frame.DataFrame:
        
        # prevent repeat api calls
        if self.steamId == steamId:
            return self.processedData
        self.steamId = steamId
        
        # get user info
        try:
            self.steamName = (await Caller.fetchData(f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.apiKey}&steamids={steamId}&format=json'))['response']['players'][0]['personaname']
        except:
            self.steamName = 'Not Available'
        
        # fetch game list in human readable DataFrame format
        try:
            self.processedData = (await Caller.fetchData(f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.apiKey}&steamid={steamId}&include_appinfo=true&format=json'))['response']['games']
        except:
            raise Exception('Could not fetch data.')
        try:
            self.processedData = pd.DataFrame(self.processedData)
            self.processedData.index = self.processedData['appid']
            self.processedData.drop(columns = ['playtime_windows_forever','playtime_mac_forever','playtime_linux_forever'],inplace=True)
            self.processedData['has_community_visible_stats'].fillna(False, inplace=True)
        except:
            raise Exception('Profile is not Public.')
            
        
        # get achievement percentage for every game that has achievements
        temp = self.processedData[self.processedData['has_community_visible_stats']].copy()
        temp['achievement_ratio'] = await asyncio.gather(*[(Caller.findAchievementRatio(await Caller.fetchData(f'http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid={appid}&key={self.apiKey}&steamid={steamId}'))) for appid in temp.index])
        self.processedData = self.processedData.merge(temp[['achievement_ratio']],right_index=True,left_index=True,how='left')
        self.processedData.drop(columns=['appid'],inplace=True)
        return self.processedData
    
    '''
    fetches json data and returns it as a python dictionary
    '''
    @staticmethod
    async def fetchData(url) -> dict:
        return json.loads(BeautifulSoup(requests.get(url).text,'html.parser').text)
    
    '''
    takes the result from a fetchData call with data about a game and
    finds the percentage of completed achievements (as a decimal)
    '''
    @staticmethod
    async def findAchievementRatio(jsonDict) -> float:
        return pd.DataFrame(jsonDict['playerstats']['achievements'])['achieved'].mean()
