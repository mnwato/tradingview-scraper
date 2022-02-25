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

VERSION = '0.0.9'
DESCRIPTION = 'Tradingview scraper tool'

# Setting up
setup(
    name="tradingview-scraper",
    version=VERSION,
    author="Mostafa Najmi",
    author_email="m.n.irib@gmail.com",
    url = 'https://github.com/mnwato/tradingview-scraper',
    download_url = 'https://github.com/mnwato/tradingview-scraper/archive/refs/tags/0.0.9.tar.gz',
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=readme(),
    License = 'MIT',
    packages=find_packages(),
    install_requires=['requests', 'pandas==1.1.5', 'beautifulsoup4==4.9.3', 'numpy'],
    keywords=['tradingview', 'scraper', 'python', 'crawler', 'financial'],
    classifiers=classifiers
)
