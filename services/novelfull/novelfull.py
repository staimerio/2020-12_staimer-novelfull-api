"""Services for novelfull controller"""
# Retic
from retic import App as app

# Requests
import requests

# bs4
from bs4 import BeautifulSoup

# Services
from retic.services.responses import success_response_service, error_response_service
from retic.services.general.urls import urlencode, slugify
from retic.services.general.json import parse

# Utils
from services.utils.general import get_node_item, get_node_light_novel_item
from services.utils.general import is_windows

# Constants
YEAR = app.config.get('NOVELFULL_YEAR', callback=int)
URL_MAIN = app.config.get('NOVELFULL_URL_MAIN')
URL_SEARCH = "/search"
INDEX = {
    u"type": 2,
    u"categories": 1,
    u"author": 0,
    u"status": 3
}


class NovelFull(object):

    def __init__(self):
        """Set the variables"""
        self.site = app.config.get("NOVELFULL_EN_SITE")
        self.host = app.config.get("NOVELFULL_EN_HOST")
        self.url_base = app.config.get("NOVELFULL_EN_URL")
        self.lang = app.config.get("NOVELFULL_EN_LANG")


def get_search(search, limit):
    """Settings environment"""
    _novelfull = NovelFull()
    """Prepare all payload"""
    _encode_url = urlencode(search)
    """Create url"""
    _page = URL_SEARCH+"?keyword="+_encode_url
    """Request to novelfull web site for latest novel"""
    _items_raw = get_list_json_items(
        _novelfull, _page, limit)
    """Validate if data exists"""
    if not _items_raw:
        """Return error if data is invalid"""
        return error_response_service(
            msg="Files not found."
        )
    """Response data"""
    return success_response_service(
        data=_items_raw
    )


def get_list_json_items(instance, page, limit):
    """Declare all variables"""
    _items = list()
    """Get article html from his website"""
    _items_json = get_list_raw_items(instance, page, limit)
    for _item_json in _items_json:
        """Validate if has the max"""
        if len(_items) >= limit:
            break
        """Slugify the item's title"""
        _item_json['slug'] = slugify(_item_json['title'])
        """Add item"""
        _items.append(_item_json)
    """Return items"""
    return _items


def get_list_raw_items(instance, page, limit):
    """Declare all variables"""
    _items = list()
    """Get article html from his website"""
    _items_raw = get_data_items_container(instance, page)
    for _item_raw in _items_raw:
        _item_data = get_data_item(instance, _item_raw)
        """Check if item exists"""
        if not _item_data:
            continue
        """Slugify the item's title"""
        _item_data['slug'] = slugify(_item_data['title'])
        """Add item"""
        _items.append(_item_data)
        """Validate if has the max"""
        if len(_items) >= limit:
            break
    """Return items"""
    return _items


def get_data_item(instance, item):
    try:
        """Find the a element"""
        _data_item = item.find('h3').find('a', href=True)
        """Get url"""
        _url = _data_item['href']
        """Check that the url exists"""
        if _url == "#":
            raise Exception('URL is invalid.')
        """Get text from data"""
        _title = _data_item.text
        _url = _url.replace(instance.url_base, "")
        return get_node_item(_url, _title, YEAR, instance.host, instance.site)
    except Exception as e:
        return None


def get_data_items_container(instance, path):
    _url = instance.url_base+path
    """Get content"""
    _content = get_text_from_req(_url)
    """Format the response"""
    _soup = BeautifulSoup(_content, 'html.parser')
    """Get container"""
    _container = _soup.find(class_='list')
    """Get all items"""
    return _container.find_all(class_='row')


def get_text_from_req(url):
    """GET Request to url"""
    _req = requests.get(url)
    """Check if status code is 200"""
    if _req.status_code != 200:
        raise Exception("The request to {0} failed".format(url))
    return _req.text


def get_chapters_by_slug(novel_slug, chapters_ids, limit=1, lang="en"):
    """Define all variables"""
    _chapters_list = []
    _publication_chapters = []
    _control = False
    """Settings environment"""
    _novelfull = NovelFull()
    """Get info about the novel from website"""
    _novel_publication = get_publication_by_slug(
        _novelfull, novel_slug
    )
    """Search all pages for the  novel"""
    for _page in range(1, 100):
        """Create new slug"""
        _novel_page_slug = novel_slug +\
            "?page={0}&per-page=50".format(_page)
        """Get all chapters references"""
        _chapters_html = get_volumes_by_slug(
            _novelfull, _novel_page_slug
        )
        """Check if it has any chapters"""
        if not _chapters_html:
            break
        """Check that chapters are new"""
        for _chapter_html in _chapters_html:
            """Check if it exists"""
            _exists = find_chapter_by_key(
                _chapter_html,
                _publication_chapters,
                "url"
            )
            if not _exists:
                _publication_chapters.append(_chapter_html)
            else:
                _control = True
        """Check if control is True"""
        if _control:
            break
    """Exclude the chapter Ids"""
    _chapters = filter(
        (lambda chapter: True if chapter['title']
         not in chapters_ids else False),
        _publication_chapters
    )
    """Get content of the all chapters"""
    for _chapter in _chapters:
        try:
            """Check the max items"""
            if len(_chapters_list) >= limit:
                break
            """Get content of the chapter by url"""
            _content = get_chapter_html_by_url(
                _novelfull, _chapter['url']
            )
            _chapters_list.append({
                **_chapter,
                u"content": _content
            })
        except Exception as e:
            continue
    """Transform data"""
    _data_response = {
        u"novel": _novel_publication,
        u"chapters": _chapters_list
    }
    """"Response to client"""
    return success_response_service(
        data=_data_response
    )


def get_publication_by_slug(instance, path):
    """Set url to consume"""
    _url = "{0}{1}".format(instance.url_base, path)
    """Get content from url"""
    _content = get_text_from_req(_url)
    """Format the response"""
    _soup = BeautifulSoup(_content, 'html.parser')
    """Get title"""
    _title = _soup.find(class_='title').text
    """Get cover"""
    _cover = instance.url_base + \
        _soup.find(class_='book').find("img", src=True)['src']
    """Get metadata"""
    _data_table = _soup.find(class_='info').find_all("div")
    """Set type"""
    _type = "Web Novel"
    """Get all categories"""
    _categories = _data_table[INDEX['categories']].text.split(
        "Genre:")[-1].split(", ")
    """Get the author"""
    _author = _data_table[INDEX['author']].find("a").text
    """Get the status"""
    _status = _data_table[INDEX['status']].find("a").text
    """Return data to request"""
    return get_node_light_novel_item(
        _url, _title, YEAR, _type, _author,
        _cover, _status, _categories, instance.lang,
        instance.host, instance.site
    )


def get_volumes_by_slug(instance, path, last_vol=0, last_ch=0):
    """Define all variables"""
    _chapters_list = []
    _control = True
    """Set url to consume"""
    _url = "{0}{1}".format(instance.url_base, path)
    """Get content from url"""
    _content = get_text_from_req(_url)
    """Format the response"""
    _soup = BeautifulSoup(_content, 'html.parser')
    """Get all chapters reference"""
    _volumes_data = _soup.\
        find(id="list-chapter").\
        find_all(class_="list-chapter")
    """For each volumen to do the following"""
    for _volume in _volumes_data:
        """Get chapter metadata"""
        _chapters_data = _volume.find_all('li')
        """For each item to do the following"""
        for _chapter in _chapters_data:
            """Get reference to chapter"""
            _chapter_data = _chapter.find('a', href=True)
            """Get the number of chapter or ignore it"""
            _number = _chapter_data['title'].\
                split("Chapter ")[-1].\
                split(" ")[0].\
                split(":")[0]

            """Get all data about the chapter"""
            _title = _chapter_data.text
            _url = _chapter_data['href']

            _chapters_list.append(
                {
                    u"title": _title,
                    u"url": _url,
                    u"number": _number,
                    u"prefix": "Chapter {0}".format(_number)
                }
            )
    return _chapters_list


def get_chapter_html_by_url(instance, path):
    """Set url"""
    _url = "{0}{1}".format(instance.url_base, path)
    """Get content from url"""
    _content = get_text_from_req(_url)
    # print title
    _content = _content.split('<hr class="chapter-end">')[1]
    """Transform data"""
    _content_html = _content
    _content_html = _content_html.\
        replace('\n', '').\
        replace('\r', '').\
        replace(">, <", "><")
    """Response content of chapter"""
    return _content_html


def find_chapter_by_key(obj, item_list, key):
    for item in item_list:
        if item[key] == obj[key]:
            return item
    return None
