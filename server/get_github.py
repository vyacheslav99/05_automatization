# -*- coding: utf-8 -*-

import logging
import argparse
import datetime
import json
import requests

GIT_URL = 'https://api.github.com'

class GitAnalizator(object):

    __request_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'}

    def __init__(self, repo, branch='master', date_start=None, date_end=None):
        self.repo = repo
        self.branch = branch
        self.date_start = date_start
        self.date_end = date_end

    def __get(self):
        pass

    def create_report(self):
        pass

def main():
    debug = False

    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--output', type=str, action='store', default=None,
                    help='Destination to write work results. File (must specify the file name in any format) or stdout (default if argument passed)')
    ap.add_argument('-r', '--repo', type=str, #action='store',
                    help='Path of the public repository for report on github.com (url without prefix "{0}", consisting of "username/repository")'.format(GIT_URL))
    ap.add_argument('-b', '--branch', type=str, action='store', default='master', help='Repository branch for report, default value "master"')
    ap.add_argument('-ds', '--date_start', type=str, action='store', default=None, help='Period for report: date start. Unlimitedly if argument passed')
    ap.add_argument('-de', '--date_end', type=str, action='store', default=None, help='Period for report: date end. Unlimitedly if argument passed')
    args = ap.parse_args()

    logging.basicConfig(filename=args.output, level=logging.DEBUG if debug else logging.INFO,
                        format='%(asctime)s %(levelname).1s %(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    logging.info('Start analyze git repository...')
    logging.info('url: {0}'.format(GIT_URL))
    logging.info('repository: {0}, branch: {1}'.format(args.repo, args.branch))
    logging.info('')

    try:
        # o = GitAnalizator(args.repo, args.branch, args.date_start, args.date_end)
        # o.create_report()
        resp = requests.post('/'.join((GIT_URL, args.repo)))
        print resp.read()
    except Exception:
        logging.exception('Error')

    logging.info('')
    logging.info('Done!')


if __name__ == '__main__':
    # vyacheslav99/01_advanced_basics
    main()
