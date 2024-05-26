import requests


data = {"content": 'Hellorld!'}
mUrl = 'https://discord.com/api/webhooks/1225936199324139660/6HQ-fuP_W7mP0yenZlO0-LMQDBSFtSEBGYdirV8ok82iRWteKng79HDUvZQfO25KsUNq'
response = requests.post(mUrl, json=data)

print(response.status_code)

print(response.content)