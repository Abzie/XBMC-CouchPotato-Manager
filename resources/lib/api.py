#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import json
from urllib import urlencode
from urllib2 import urlopen, Request, HTTPError, URLError
from hashlib import md5


class AuthenticationError(Exception):
    pass


class ConnectionError(Exception):
    pass


class CouchPotatoApi():

    def __init__(self, *args, **kwargs):
        self._reset_connection()
        if args or kwargs:
            self.connect(*args, **kwargs)

    def _reset_connection(self):
        self.connected = False
        self.hostname = None
        self.port = None
        self.use_https = None
        self.username = None
        self.password = None
        self.api_key = None

    def connect(self, hostname, port, use_https=False,
                username=None, password=None, api_key=None):
        self.log(
            'connect: hostname="%s", port="%s", '
            'use_https="%s", username="%s", api_key="%s"'
            % (hostname, port, use_https, username, api_key)
        )
        self.hostname = hostname
        self.port = port
        self.use_https = use_https
        self.username = username
        self.password = password
        self.api_key = api_key
        if self.api_key:
            self.log('trying api_key...')
            try:
                json_data = self._api_call('app.available')
            except AuthenticationError:
                self.log('trying api_key: failed')
            else:
                self.log('trying api_key: success')
                self.connected = True
        if not self.connected:
            self.connected = self._get_api_key()
        if not self.connected:
            self._reset_connection()
            raise AuthenticationError
        return self.api_key

    def get_status_list(self):
        return self._api_call('status.list').get('list', [])

    def get_movies(self, status=None):
        if status:
            params = {'release_status': status}
        else:
            params = {}
        return self._api_call('movie.list', params).get('movies', [])

    def search_wanted(self, search_title):
        params = {
            'q': search_title
        }
        return self._api_call('movie.search', params).get('movies', [])

    def add_wanted(self, profile_id, movie_identifier, movie_title):
        params = {
            'profile_id': profile_id,
            'identifier': movie_identifier,
            'title': movie_title.encode('latin1', 'ignore')
        }
        return self._api_call('movie.add', params).get('added')

    def refresh_releases(self, library_id):
        params = {
            'id': library_id
        }
        return self._api_call('movie.refresh', params).get('success')

    def delete_movie(self, library_id):
        params = {
            'id': library_id,
        }
        return self._api_call('movie.delete', params).get('success')

    def delete_release(self, release_id):
        params = {
            'id': release_id
        }
        return self._api_call('release.delete', params).get('success')

    def download_release(self, release_id):
        params = {
            'id': release_id
        }
        return self._api_call('release.download', params).get('success')

    def ignore_release(self, release_id):
        params = {
            'id': release_id
        }
        return self._api_call('release.ignore', params).get('success')

    def get_profiles(self):
        return self._api_call('profile.list').get('list', [])

    def _get_api_key(self):
        self.log('_get_api_key: username="%s"' % self.username)
        params = {
            'u': md5(self.username.decode('latin1')).hexdigest(),
            'p': md5(self.password.decode('latin1')).hexdigest()
        }
        url = '%s/getkey/?%s' % (self._api_url, urlencode(params))
        try:
            json_data = json.load(urlopen(Request(url)))
        except URLError:
            raise ConnectionError
        if json_data.get('success') and json_data.get('api_key'):
            api_key = json_data['api_key']
            self.api_key = api_key
            return True
        return False

    def _api_call(self, endpoint, params=None):
        self.log('_api_call started with endpoint=%s, params=%s'
                 % (endpoint, params))
        url = '%s/api/%s/%s/' % (self._api_url, self.api_key, endpoint)
        if params:
            url += '?%s' % urlencode(params)
        # self.log('_api_call using url: %s' % url)
        try:
            response = urlopen(Request(url))
            json_data = json.load(response)
        except HTTPError, error:
            self.log('__urlopen HTTPError: %s' % error)
            if error.fp.read() == 'Wrong API key used':
                raise AuthenticationError
            else:
                raise ConnectionError
        except URLError:
            raise ConnectionError
        # self.log('_api_call response: %s' % repr(json_data))
        return json_data

    @property
    def _api_url(self):
        proto = 'https' if self.use_https else 'http'
        return '%s://%s:%s' % (proto, self.hostname, self.port)

    def log(self, text):
        print u'[%s]: %s' % (self.__class__.__name__, repr(text))