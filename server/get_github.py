# -*- coding: utf-8 -*-

# import logging
import argparse
import datetime
import requests
import warnings

try:
    from secret import proxy_user, proxy_pass, proxy_addr
except:
    proxy_user = None
    proxy_pass = None
    proxy_addr = None

# по поводу сертификата ssl вылезает warning. Сейчас не буду заморачиваться на его счет, просто скрою
warnings.filterwarnings('ignore')


class GitAnalizator():

    __api_git_url = 'https://api.github.com'
    __headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'}

    def __init__(self, repo, branch=None, date_start=None, date_end=None, auth_user=None, auth_pass=None):
        proxy = '{0}{1}/'.format('{0}:{1}@'.format(proxy_user, proxy_pass),
                                 proxy_addr) if proxy_user and proxy_pass and proxy_addr else None
        self.__proxies = {p: '://'.join((p, proxy)) for p in ('http', 'https')} if proxy else None
        self.full_name = repo
        self.user, self.repo = self.__parse_addr(repo)
        self.branch = branch or 'master'
        self.date_start = datetime.datetime.strptime(date_start, '%d.%m.%Y') if date_start else None
        self.date_end = datetime.datetime.strptime(date_end, '%d.%m.%Y') if date_end else None
        self.since = datetime.datetime.strptime(date_start, '%d.%m.%Y').isoformat() if date_start else None
        self.until = datetime.datetime.strptime(date_end, '%d.%m.%Y').isoformat() if date_end else None
        self.auth_user = auth_user
        self.auth_pass = auth_pass
        #self.session = requests.Session()
        #self.__do_auth()

    # def __do_auth(self):
    #     if self.auth_user and self.auth_pass:
    #         r = self.session.post('https://api.github.com/user', {'action': 'auth', 'login': self.auth_user, 'password': self.auth_pass})
    #         print r.content

    def __get_auth(self):
        return (self.auth_user, self.auth_pass) if self.auth_user and self.auth_pass else None

    def __query_data(self, path, is_absolute=False, params=None, limit_pages=0, break_on_date=None):
        """
        Запрашивает данные по конкретному адресу, возвращает объект json

        :param path: запрашиваемый url
        :param is_absolute: bool, path включает имя хоста или нет, т.е. это полный url или относительный
        :param params: параметры запроса, словарь
        :param limit_pages: вызвать исключение если ответ содержит страниц больше, чем тут задано. 0 - не ограничивать
        :param break_on_date: остановить запрос остальных страниц, как только последний эл-т текщего списка будет содержать
            дату меньше заданной. Словарь с ключами: 'date' - дата для сравнения, 'item_key' - имя ключа в словаре (эл-те списка)
            содержащего сравниваемую дату
        :return: json пришедший с ответом от сервера
        """

        resp = requests.get(path if is_absolute else '/'.join((self.__api_git_url, path)), params=params, verify=False,
                            headers=self.__headers, proxies=self.__proxies, auth=self.__get_auth())
        # resp = self.session.get(path if is_absolute else '/'.join((self.__api_git_url, path)), params=params, verify=False,
        #                         headers=self.__headers, proxies=self.__proxies)

        d = resp.json()
        if resp.ok:
            # списки сервер выдает постранично и если в ответе есть ссылка на следующую страницу - запрашиваем ее и добавляем к результату.

            if limit_pages > 0:
                # Ограничение на кол-во страниц, слишком много страниц листать не получиться, по нескольким причинам
                # (и из-за времени и из-за ограничений на сервере api.github.com, связанных с их политикой ограничения кол-ва
                # обращений к api с одного хоста)

                last = resp.links.get('last', None)
                if last:
                    total_pages = int(last['url'].split('page=')[1])
                    if total_pages > limit_pages:
                        raise Exception('Server returned too much data ({0} pages, {1} rows each)! '
                                        'Set a shorter period for analysis and try again'.format(total_pages, len(d)))

            url = resp.links.get('next', None)
            if url:
                if not (break_on_date and
                    datetime.datetime.strptime(d[-1][break_on_date['item_key']], "%Y-%m-%dT%H:%M:%SZ") < break_on_date['date']):
                    next_page = self.__query_data(url['url'], is_absolute=True)
                    if next_page:
                        d.extend(next_page)

            return d
        else:
            raise Exception(d.get('message', resp.content))

    def __parse_addr(self, addr):
        # Разбивает путь на части "имя пользователя" и "название репозитория", возвращает: user, repo
        parts = addr.split('/')
        if len(parts) == 1:
            return parts[0], None
        else:
            return parts[0], parts[1]

    def __fmt_print(self, caption, strings):
        """
        Вывод на печать данных массива, проедставляющего собой список списков
        Подгоняет шрину колонок под самую широкую запись в колонке, оформляет в виде таблички.

        :param caption: list or tuple: шапка, должна содержать столько же эл-тов, сколько в каждой строке списка strings
        :param strings: list or tuple: массив данных, которые нало вывести на печать
        :return: None
        """
        strings.insert(0, caption)
        col_lengths = []
        total_len = 0

        for col in range(len(strings[0])):
            col_lengths.append(max(len(str(row[col])) for row in strings) + 2)
            total_len += col_lengths[-1]

        for n, row in enumerate(strings):
            if n == 1:
                print('-' * (total_len + 1))
            print('|  '.join(str(s).ljust(col_lengths[i]) for i, s in enumerate(row)))

    def __calc_reqs(self, req_list, old_days=0):
        res = 0
        old = 0

        for req in req_list:
            # если задан диапазон и мы в него не попали, пропускаем
            created_at = datetime.datetime.strptime(req['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            if (self.date_start and created_at < self.date_start) or (self.date_end and created_at > self.date_end):
                continue
            res += 1

            # посчитаем старые
            if old_days > 0 and (datetime.datetime.today() - created_at).days > old_days:
                old += 1

        return res, old

    def __calc_issues(self, issues_list, old_days=0):
        res = 0
        old = 0

        for iss in issues_list:
            created_at = datetime.datetime.strptime(iss['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            if (self.date_start and created_at < self.date_start) or (self.date_end and created_at > self.date_end) or (
                iss['repository']['full_name'] != self.full_name):
                continue
            res += 1

            if old_days > 0 and (datetime.datetime.today() - created_at).days > old_days:
                old += 1

        return res, old

    def _list_repos(self):
        # возвращает список названий публичных репозиториев пользователя
        repos = self.__query_data('/'.join(('users', self.user, 'repos')))
        for repo in repos:
            if not repo['private']:
                yield repo['name']

    def _get_activity(self):
        """
        1. Самые активные участники. Таблица: login автора, кол-во его коммитов. Сортировка по убыванию кол-ва коммитов. макс 30 строк.
            GET /repos/:owner/:repo/commits, вернет список коммитов за период
            params:
                sha: branch_key or branch_name, default master
                since: Only commits after this date, ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
                until: Only commits before this date, ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ

            или через статистику: GET /repos/:owner/:repo/stats/contributors, вернет список авторов и кол-во коммитов.
            Но тут нет возможности ограничить по периоду (максимум понедельно, и то - забрать все, а потом локально
            срезать данные вне периода), поэтому нам не подходит.
        """
        params = {}
        params['sha'] = self.branch
        if self.since: params['since'] = self.since
        if self.until: params['until'] = self.until
        commits = self.__query_data('/'.join(('repos', self.user, self.repo, 'commits')), params=params, limit_pages=10)

        data = {}
        for commit in commits:
            k = 'author' if commit['author'] else 'committer'
            if isinstance(commit[k], dict):
                if commit[k]['login'] in data:
                    data[commit[k]['login']] += 1
                else:
                    data[commit[k]['login']] = 1

        return sorted(data.items(), key=lambda i: i[1], reverse=True)[:30]

    def _get_pull_requests(self):
        """
        2. Кол-во открытых и закрытых pull requests.
        3. Кол-во старых pull requests. Pull request считается старым, если он не закрывается в течение 30 дней
        GET /repos/:owner/:repo/pulls
        params:
            state: open, closed, all. default open
            base: фильтр по принадлежности к branch
            sort: сортировка: created, updated, popularity (comment count) or long-running
            direction: asc, desc. default desc
        """

        stop_fetch_params = {'date': self.date_start, 'item_key': 'created_at'}
        opened, old = self.__calc_reqs(self.__query_data('/'.join(('repos', self.user, self.repo, 'pulls')),
            params={'base': self.branch, 'state': 'open', 'sort': 'created'}, break_on_date=stop_fetch_params), old_days=30)
        closed, _ = self.__calc_reqs(self.__query_data('/'.join(('repos', self.user, self.repo, 'pulls')),
            params={'base': self.branch, 'state': 'closed', 'sort': 'created'}, break_on_date=stop_fetch_params))

        return opened, closed, old

    def _get_issues(self):
        """
        4. Кол-во открытых и закрытых issues.
        5. Кол-во старых issues. Issue считается старым, если он не закрывается в течение 14 дней
        GET /user/issues, только если авторизован
        params:
            state: open, closed, all. default open
            sort: created, updated, comments. Default: created
            direction: asc, desc. default desc
            since: Only issues updated at or after this time are returned. ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
        """

        stop_fetch_params = {'date': self.date_start, 'item_key': 'created_at'}
        opened, old = self.__calc_issues(self.__query_data('/'.join(('user', 'issues')), params={'state': 'open'},
            break_on_date=stop_fetch_params), old_days=14)
        closed, _ = self.__calc_issues(self.__query_data('/'.join(('user', 'issues')), params={'state': 'closed'},
            break_on_date=stop_fetch_params))

        return opened, closed, old

    def do_report(self):
        if not self.repo:
            print('Not specified user repository name!')
            print('The following repositories are available to the user {0}:'.format(self.user))
            for repo in self._list_repos():
                print(repo)
        else:
            print('Commits activity:')
            self.__fmt_print(('Author', 'commits'), self._get_activity())
            print('')

            print('Pull requests:')
            opened, closed, old = self._get_pull_requests()
            print('\tOpened: {0}'.format(opened))
            print('\tClosed: {0}'.format(closed))
            print('\tOld:    {0}'.format(old))
            print('')

            print('Issues:')
            if not self.__get_auth():
                print('Authorization is required to obtain information about issues')
            else:
                opened, closed, old = self._get_issues()
                print('\tOpened: {0}'.format(opened))
                print('\tClosed: {0}'.format(closed))
                print('\tOld:    {0}'.format(old))


def main():
    debug = True

    ap = argparse.ArgumentParser()
    # ap.add_argument('-o', '--output', type=str, action='store', default=None,
    #     help='Destination to write work results. File (must specify the file name in any format) or stdout (default if argument passed)')
    # добавил возможность авторизоваться, т.к. это дает некоторые плюсы - например увеличивает ограничение на кол-во вызовов API сервера...
    ap.add_argument('-u', '--user', type=str, help='User name for authentication on github.com')
    ap.add_argument('-p', '--password', type=str, help='Password for authentication on github.com')
    ap.add_argument('-r', '--repo', type=str, required=True,
        help='Path of the public repository for report on github (url without prefix "https://github.com", consisting of "username/repository")')
    ap.add_argument('-b', '--branch', type=str, action='store', help='Repository branch for report, default value "master"')
    ap.add_argument('-ds', '--date_start', type=str, action='store',
                    help='Period for report: date start (format d.m.Y). Unlimitedly if argument passed')
    ap.add_argument('-de', '--date_end', type=str, action='store',
                    help='Period for report: date end (format d.m.Y). Unlimitedly if argument passed')
    args = ap.parse_args()

    # logging.basicConfig(filename=args.output, level=logging.DEBUG if debug else logging.INFO,
    #                     format='%(asctime)s %(levelname).1s %(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    print('Start analyze git repository...')
    print('repository: {0}, branch: {1}'.format(args.repo, args.branch or 'master'))
    print('')

    try:
        obj = GitAnalizator(args.repo, args.branch, args.date_start, args.date_end, auth_user=args.user, auth_pass=args.password)
        obj.do_report()
    except Exception as e:
        if debug:
            #logging.exception('Error')
            raise
        else:
            print(e)

    print('')
    print('Done!')


if __name__ == '__main__':
    main()
