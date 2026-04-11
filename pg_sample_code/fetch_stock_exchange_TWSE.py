import requests
import pandas as pd
import time
from tqdm import tqdm
import datetime
from db_util import db99exec

def main(da):
    market = 'tw'

    time_stamp = int(time.time())
    print(time_stamp)
    date = str(da).replace('-','')
    url = 'https://www.twse.com.tw/rwd/zh/fund/T86?date=20240606&selectType=ALL&response=json&_=1718087663302'
    url = f'https://www.twse.com.tw/rwd/zh/fund/T86?date={date}&selectType=ALL&response=json&_={time_stamp}'

    response = requests.get(url)
    data = response.json()

    #fields = data['fields']
    fields = ['code',
              'cname',
              'foreign_investment_buy_volume',
              'foreign_investment_sell_volume',
              'foreign_investment_net_buy_volume',
              'foreign_proprietary_traders_buy_volume',
              'foreign_proprietary_traders_sell_volume',
              'foreign_proprietary_traders_net_buy_volume',
              'investment_trust_buy_volume',
              'investment_trust_sell_volume',
              'investment_trust_net_buy_volume',
              'proprietary_traders_net_buy_volume',
              'proprietary_traders_buy_volume_self',
              'proprietary_traders_sell_volume_self',
              'proprietary_traders_net_buy_volume_self',
              'proprietary_traders_buy_volume_hedging',
              'proprietary_traders_sell_volume_hedging',
              'proprietary_traders_net_buy_volume_hedging',
              'net_buy_volume_by_three_legal_entities']

    rows = data['data']

    df = pd.DataFrame(rows, columns=fields)

    ins_sql = ''
    keys = 'three_legal_pkey'
    print(da)
    for index, row in tqdm(df.iterrows(), total=len(df)):
        volumes = {key: int(str(row[key] or '0').replace(',', '')) for key in ['foreign_investment_buy_volume',
                                                                               'foreign_investment_sell_volume',
                                                                               'foreign_investment_net_buy_volume',
                                                                               'foreign_proprietary_traders_buy_volume',
                                                                               'foreign_proprietary_traders_sell_volume',
                                                                               'foreign_proprietary_traders_net_buy_volume',
                                                                               'investment_trust_buy_volume',
                                                                               'investment_trust_sell_volume',
                                                                               'investment_trust_net_buy_volume',
                                                                               'proprietary_traders_net_buy_volume',
                                                                               'proprietary_traders_buy_volume_self',
                                                                               'proprietary_traders_sell_volume_self',
                                                                               'proprietary_traders_net_buy_volume_self',
                                                                               'proprietary_traders_buy_volume_hedging',
                                                                               'proprietary_traders_sell_volume_hedging',
                                                                               'proprietary_traders_net_buy_volume_hedging',
                                                                               'net_buy_volume_by_three_legal_entities']}

        ins_sql += f"""
        INSERT INTO three_legal_info(
            da,
            code, 
            cname, 
            foreign_investment_buy_volume, 
            foreign_investment_sell_volume, 
            foreign_investment_net_buy_volume, 
            foreign_proprietary_traders_buy_volume, 
            foreign_proprietary_traders_sell_volume, 
            foreign_proprietary_traders_net_buy_volume, 
            investment_trust_buy_volume, 
            investment_trust_sell_volume, 
            investment_trust_net_buy_volume, 
            proprietary_traders_net_buy_volume, 
            proprietary_traders_buy_volume_self, 
            proprietary_traders_sell_volume_self, 
            proprietary_traders_net_buy_volume_self, 
            proprietary_traders_buy_volume_hedging, 
            proprietary_traders_sell_volume_hedging, 
            proprietary_traders_net_buy_volume_hedging, 
            net_buy_volume_by_three_legal_entities
        )
        VALUES (
            '{da}', 
            '{row['code']} TT Equity', 
            '{row['cname']}', 
            {volumes['foreign_investment_buy_volume']}, 
            {volumes['foreign_investment_sell_volume']}, 
            {volumes['foreign_investment_net_buy_volume']}, 
            {volumes['foreign_proprietary_traders_buy_volume']}, 
            {volumes['foreign_proprietary_traders_sell_volume']}, 
            {volumes['foreign_proprietary_traders_net_buy_volume']}, 
            {volumes['investment_trust_buy_volume']}, 
            {volumes['investment_trust_sell_volume']}, 
            {volumes['investment_trust_net_buy_volume']}, 
            {volumes['proprietary_traders_net_buy_volume']}, 
            {volumes['proprietary_traders_buy_volume_self']}, 
            {volumes['proprietary_traders_sell_volume_self']}, 
            {volumes['proprietary_traders_net_buy_volume_self']}, 
            {volumes['proprietary_traders_buy_volume_hedging']}, 
            {volumes['proprietary_traders_sell_volume_hedging']}, 
            {volumes['proprietary_traders_net_buy_volume_hedging']}, 
            {volumes['net_buy_volume_by_three_legal_entities']}
        )ON CONFLICT ON CONSTRAINT {keys} DO NOTHING;
        """

    print(ins_sql)
    error = db99exec(market, ins_sql)
    if error != None:
        print(error)
    a = 123

if __name__ == "__main__":

    start_da = '2024-07-23'
    # start_da = '2025-01-01'
    # start_da = '2004-07-23'
    start_da = '2024-12-31'
    start_da = '2025-12-31'
    end_da = str(datetime.datetime.today())[0:10]

    daList = [date.strftime('%Y-%m-%d')
              for date in pd.date_range(start=start_da, end=end_da)
              if date.weekday() < 5]

    # start_da = '2017-12-08'
    # end_da = '2024-12-08'
    for da in tqdm(daList[::-1]):
    #for da in tqdm(daList):
        try:
            main(da)
        except Exception as err:
            print(err)


