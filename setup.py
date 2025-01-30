from setuptools import setup, find_packages

def readme():
    with open('README.md') as f:
        README = f.read()
    return README
 
classifiers = [
  'Development Status :: 2 - Pre-Alpha',
  'Intended Audience :: Developers',
  'Operating System :: OS Independent',
  'License :: OSI Approved :: MIT License',
  'Programming Language :: Python :: 3.8'
]

VERSION = '0.4.2'
DESCRIPTION = 'Tradingview scraper tool'

# Setting up
setup(
    name="tradingview-scraper",
    version=VERSION,
    author="Mostafa Najmi",
    author_email="m.n.irib@gmail.com",
    url='https://github.com/mnwato/tradingview-scraper',
    download_url='https://github.com/mnwato/tradingview-scraper/archive/refs/tags/0.4.0.zip',
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=readme(),
    license='MIT',
    packages=find_packages(),
    package_data={
        'tradingview_scraper': [
            'data/areas.json',
            'data/exchanges.txt',
            'data/indicators.txt',
            'data/languages.json',
            'data/news_providers.txt',
            'data/timeframes.json',
        ],
    },
    install_requires=[
        "requests>=2.32.3",
        "pandas>=2.0.3",
        "beautifulsoup4>=4.12.3",
        "pydantic>=2.8.2",
        "websockets>=13.1",
        "websocket-client>=1.8.0",
    ],
    keywords=['tradingview', 'scraper', 'python', 'crawler', 'financial'],
    classifiers=classifiers
)
