from setuptools import setup

setup(
   name='MusicBot',
   version='1.0',
   description='A useful module',
   author='Ryan',
   author_email='ryanstack10@gmail.com',
   packages=['MusicBot'],  #same as name
   install_requires=['youtube_dl', 'discord', 'python-dotenv', 'youtube_search', 'yt_dlp'], #external packages as dependencies
)