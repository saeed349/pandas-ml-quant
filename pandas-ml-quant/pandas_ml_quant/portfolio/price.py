from collections import defaultdict
from datetime import timedelta
from typing import Union, Tuple

import pandas as pd
from bintrees import BinaryTree

from pandas_ml_common.utils.time_utils import parse_timestamp


class PriceTimeSeries(object):
    """
    entweder senden wir einen timestamp zusammen mit bid/ask, oder einer Quote mit spread (default 0).
    man kann auch einen bar (aka candle) senden mit open und close timestamps. default wird ein bar aber so übersetzt:

        open = 00:00:00.0001
        close = 00:00:00.0000 am nächsten Tag!

    wenn wir den Trade mit 23.59.59 machen dann ist der aktuellste Kurs der Open des Tages. was eigentlich logisch ist,
    bei einer ein datenquelle bekommen wir den Kurs erst am Ende des Tages. der früheste Trade kann also nur morgen mit
    dem open stattfinden. trades um Mitternacht werden mit dem close des Vortages ausgeführt.

    bei jeder Strategie muss man jetzt überlegen. wenn ich das Signal heute bekomme (eod). dann kann ich frühestens
    heute Morgen den Trade platzieren. entweder zum open Morgen also irgendwann nach Mitternacht. oder zum close von
    heute (angenommen man hat ein realtime feed) also morgen um exakt Mitternacht.

    idealerweise bauen wir ein library das Signale in trades übersetzt damit wir die für den user etwas einfacher
    abstrahieren können.
    """

    def __init__(self):
        self.timeseries = defaultdict(BinaryTree)

    def push_bar(self,
                 instrument: str,
                 date: Union[pd.Timestamp, str, Tuple[str, str]],
                 open: float,
                 high: float = None,
                 low: float = None,
                 close: float = None,
                 volume: float = None,
                 currency: str = 'USD',
                 open_time: str = '00:00:00.0001',
                 close_time: str = '00:00:00.0000',
                 spread: float = 0,
                 ):
        assert close != None, 'close price need to be passed'

        # high, low and volume are actually not used at all it is really just for convenience
        open_timestamp = parse_timestamp(f'{date} {open_time}')
        close_timestamp = parse_timestamp(f'{date} {close_time}')

        if close_timestamp < open_timestamp:
            close_timestamp = close_timestamp + timedelta(days=1)

        self.push_price(instrument, open_timestamp, open, currency, spread)
        self.push_price(instrument, close_timestamp, close, currency, spread)

    def push_price(self,
                   instrument: str,
                   timestamp: Union[pd.Timestamp, str, Tuple[str, str]],
                   price: float,
                   currency: str = 'USD',
                   spread: float = 0,
                  ):
        assert 0 <= spread <= 1, 'Spread need to be between 0 and 1'
        bid = price * (1 - spread / 2)
        ask = price * (1 + spread / 2)
        self.push_quote(instrument, timestamp, bid, ask, currency)

    def push_quote(self,
                   instrument: str,
                   timestamp: Union[pd.Timestamp, str, Tuple[str, str]],
                   bid: float,
                   ask: float,
                   currency: str = 'USD',
                  ):
        tst = parse_timestamp(timestamp)
        self.timeseries[(instrument, currency)][tst] = bid, ask

    def get_price(self, instrument: str, timestamp: Union[pd.Timestamp, str, Tuple[str, str]], currency: str = 'USD'):
        tst = parse_timestamp(timestamp)
        return self.timeseries[(instrument, currency)].floor_item(tst)
