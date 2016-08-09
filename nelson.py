import argparse
import http.client
import logging
import json
import shelve
import time

import bs4


logging.basicConfig(
    format='%(levelname)s - %(message)s',
    level=logging.INFO,
)

parser = argparse.ArgumentParser(description='Slackbot for french medals')
parser.add_argument('--hook', help="https://hooks.slack.com/services/{HOOK}")

args = parser.parse_args()

first_run = True

while True:
    rio_conn = http.client.HTTPSConnection('www.rio2016.com')
    rio_conn.request('GET', '/en/medal-count-country')
    resp = rio_conn.getresponse()

    soup = bs4.BeautifulSoup(resp.read(), 'html.parser')

    fra = soup.body.find(
        'tr', attrs={'data-odfcode': 'FRA'}).next_sibling.next_sibling
    medals = []

    for type_ in fra.find_all('tr', class_='type'):
        color = type_.find('span', class_='medal-name').contents[0]
        while True:
            medals.append({
                'color': color,
                'sport': type_.find('td', class_='col-2').strong.contents[0],
                'event': type_.find('td', class_='col-3').a.contents[0],
                'athlete': type_.find('td', class_='col-4').contents[0],
            })
            type_ = type_.next_sibling.next_sibling
            try:
                if type_ is None or 'type' in type_['class']:
                    break       # scanned all the medal of this type
            except KeyError:
                continue
    logging.info('parsed {:d} medals'.format(len(medals)))

    with shelve.open('medals_db') as medals_db: # use a shelf as a persistent set
        for m in medals:
            key = json.dumps(m, sort_keys=True)
            if key not in medals_db:
                logging.info('new medal: {}'.format(key))
                medals_db[key] = True

                # on first run only populate db
                if not first_run:
                    slack_conn = http.client.HTTPSConnection("hooks.slack.com")
                    slack_conn.request(
                        'POST', '/services/{}'.format(args.hook),
                        json.dumps({
                            'username': 'Nelson Monfort',
                            'icon_url': 'http://i.imgur.com/ZRrFidN.png',
                            'text': (
                                'Incroyable! Incredible! {athlete} gives France a '
                                'new {color} medal in {sport}: {event}').format(**m)
                        }))

    first_run = False
    time.sleep(20)
