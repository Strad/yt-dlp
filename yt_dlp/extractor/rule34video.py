import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    clean_html,
    extract_attributes,
    get_element_by_attribute,
    get_element_by_class,
    get_element_html_by_class,
    get_elements_by_class,
    int_or_none,
    parse_count,
    parse_duration,
    unescapeHTML,
    ExtractorError,
    urlencode_postdata
)
from yt_dlp.extractor import generic
from urllib.parse import urlparse, urlunparse
from yt_dlp.utils.traversal import traverse_obj


class Rule34VideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/videos?/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://rule34video.com/video/3065157/shot-it-mmd-hmv/',
            'md5': 'ffccac2c23799dabbd192621ae4d04f3',
            'info_dict': {
                'id': '3065157',
                'ext': 'mp4',
                'title': 'Shot It-(mmd hmv)',
                'thumbnail': 'https://rule34video.com/contents/videos_screenshots/3065000/3065157/preview.jpg',
                'duration': 347.0,
                'age_limit': 18,
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'timestamp': 1639872000,
                'description': 'https://discord.gg/aBqPrHSHvv',
                'upload_date': '20211219',
                'uploader': 'Sweet HMV',
                'uploader_url': 'https://rule34video.com/members/22119/',
                'categories': ['3D', 'MMD', 'iwara'],
                'tags': 'mincount:10',
            },
        },
        {
            'url': 'https://rule34video.com/videos/3065296/lara-in-trouble-ep-7-wildeerstudio/',
            'md5': '6bb5169f9f6b38cd70882bf2e64f6b86',
            'info_dict': {
                'id': '3065296',
                'ext': 'mp4',
                'title': 'Lara in Trouble Ep. 7 [WildeerStudio]',
                'thumbnail': 'https://rule34video.com/contents/videos_screenshots/3065000/3065296/preview.jpg',
                'duration': 938.0,
                'age_limit': 18,
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'timestamp': 1640131200,
                'description': '',
                'creators': ['WildeerStudio'],
                'upload_date': '20211222',
                'uploader': 'CerZule',
                'uploader_url': 'https://rule34video.com/members/36281/',
                'categories': ['3D', 'Tomb Raider'],
                'tags': 'mincount:40',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats = []

        for mobj in re.finditer(r'<a[^>]+href="(?P<video_url>[^"]+download=true[^"]+)".*>(?P<ext>[^\s]+) (?P<quality>[^<]+)p</a>', webpage):
            url, ext, quality = mobj.groups()
            formats.append({
                'url': url,
                'ext': ext.lower(),
                'quality': quality,
            })

        categories, creators, uploader, uploader_url = [None] * 4
        for col in get_elements_by_class('col', webpage):
            label = clean_html(get_element_by_class('label', col))
            if label == 'Categories':
                categories = list(map(clean_html, get_elements_by_class('item', col)))
            elif label == 'Artist':
                creators = list(map(clean_html, get_elements_by_class('item', col)))
            elif label == 'Uploaded by':
                # Find the anchor tag for the uploader name
                uploader_anchor = get_element_html_by_class('item btn_link', col) or ''
                uploader = clean_html(uploader_anchor)
                uploader_url = extract_attributes(uploader_anchor).get('href')

        return {
            **traverse_obj(self._search_json_ld(webpage, video_id, default={}), ({
                'title': 'title',
                'view_count': 'view_count',
                'like_count': 'like_count',
                'duration': 'duration',
                'timestamp': 'timestamp',
                'description': 'description',
                'thumbnail': ('thumbnails', 0, 'url'),
            })),
            'id': video_id,
            'formats': formats,
            'title': self._html_extract_title(webpage),
            'thumbnail': self._html_search_regex(
                r'preview_url:\s+\'([^\']+)\'', webpage, 'thumbnail', default=None),
            'duration': parse_duration(self._html_search_regex(
                r'"icon-clock"></i>\s+<span>((?:\d+:?)+)', webpage, 'duration', default=None)),
            'view_count': int_or_none(self._html_search_regex(
                r'"icon-eye"></i>\s+<span>([ \d]+)', webpage, 'views', default='').replace(' ', '')),
            'like_count': parse_count(get_element_by_class('voters count', webpage)),
            'comment_count': int_or_none(self._search_regex(
                r'[^(]+\((\d+)\)', get_element_by_attribute('href', '#tab_comments', webpage), 'comment count', fatal=False)),
            'age_limit': 18,
            'creators': creators,
            'uploader': uploader,
            'uploader_url': uploader_url,
            'categories': categories,
            'tags': list(map(unescapeHTML, re.findall(
                r'<a class="tag_item"[^>]+\bhref="https://rule34video\.com/tags/\d+/"[^>]*>(?P<tag>[^>]*)</a>', webpage))),
        }

class Rule34VideoUserIE(InfoExtractor):
    IE_NAME = 'rule34video:user'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/members/(?P<id>\d+)(?:/(?:videos|favourites/videos|playlists)/?)?'

    _TESTS = [{
        'url': 'https://rule34video.com/members/1613548/',
        'info_dict': {
            'id': '1613548',
            'title': 'EchobunnyMV',
            'uploader_id': '1613548',
            'uploader': 'EchobunnyMV',
            'description': str,
            'thumbnails': list,
        },
        'playlist_mincount': 10,
        'params': {'skip_download': True},
    }]

    def _fetch_page(self, user_id, display_id, page):
        # The site accepts both '2' and '02' so zero-pad to match their markup
        page_param = f'{page:02d}'
        ajax_url = (
            f'https://rule34video.com/members/{user_id}/videos/'
            f'?mode=async&function=get_block&block_id=list_videos_uploaded_videos'
            f'&sort_by=&from_videos={page_param}'
        )
        html = self._download_webpage(
            ajax_url, display_id, note=f'Downloading user videos page {page}', fatal=False) or ''

        for m in re.finditer(
            r'<a\s+class="th[^"]*"\s+href="(?P<href>https?://rule34video\.com/video/\d+/[^"]+)"',
            html):
            yield self.url_result(m.group('href'), ie=Rule34VideoIE.ie_key())

        has_next = re.search(
            rf'data-parameters="[^"]*from_videos:(?:{page+1:02d}|{page+1})[^"]*"', html)
        if has_next:
            yield None 

    def _real_extract(self, url):
        user_id = self._match_id(url)

        profile_url = f'https://rule34video.com/members/{user_id}/'
        profile = self._download_webpage(profile_url, user_id)

        name = (self._html_search_regex(r'<h2 class="title">\s*(.*?)\s*</h2>', profile, 'name', default=None)
                or self._html_search_regex(r'<title>([^<]+?)\'s Page</title>', profile, 'title', default=None))

        avatar = self._search_regex(
            r'<div class="avatar">\s*<img[^>]+src="([^"]+)"',
            profile, 'avatar', default=None)

        about = clean_html(self._search_regex(
            r'<div class="bottom_description">[\s\S]*?<div class="row">([\s\S]*?)</div>',
            profile, 'about', default=''))

        entries, page = [], 1
        while True:
            saw_items = False
            for item in self._fetch_page(user_id, user_id, page):
                if item is None:
                    continue
                entries.append(item)
                saw_items = True
            if not saw_items:
                break
            page += 1

        playlist = self.playlist_result(entries, playlist_id=user_id, playlist_title=name)
        if avatar:
            playlist['thumbnails'] = [{'url': avatar}]
        if about:
            playlist['description'] = about
        playlist['uploader'] = name
        playlist['uploader_id'] = user_id
        return playlist
