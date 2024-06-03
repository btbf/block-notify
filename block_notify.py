#!/usr/bin/python3

import os
import time
import datetime
import sqlite3
import requests
import slackweb
import subprocess
import i18n
import json
import pathlib
import configparser
import sys
import pytz
from pytz import timezone
from dateutil import parser
from discordwebhook import Discord
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
from os.path import dirname


#Configファイル読み込み
config_path = pathlib.Path(__file__).parent.absolute() / "config.ini"
config = configparser.ConfigParser()
config.read(config_path)

version = "2.2.2"

#設定値代入
guild_db_dir = config['PATH']['guild_db_dir']
shelley_genesis = config['PATH']['shelley_genesis']
byron_genesis = config['PATH']['byron_genesis']
pool_ticker = config['NOTIFY_SETTINGS']['pool_ticker']
line_notify_token = config['NOTIFY_API_KEY']['line_notify_token']
discord_webhook_url = config['NOTIFY_API_KEY']['discord_webhook_url']
slack_webhook_url = config['NOTIFY_API_KEY']['slack_webhook_url']
telegram_token = config['NOTIFY_API_KEY']['telegram_token']
telegram_id = config['NOTIFY_API_KEY']['telegram_id']
notify_language = config['NOTIFY_SETTINGS']['notify_language']
notify_timezone = config['NOTIFY_SETTINGS']['notify_timezone']
notify_platform = config['NOTIFY_SETTINGS']['notify_platform']
notify_level = config['NOTIFY_SETTINGS']['notify_level']
nextepoch_leader_date = config['NOTIFY_SETTINGS']['nextepoch_leader_date']
prometheus_port = config['NOTIFY_SETTINGS']['prometheus_port']

guild_db_name = "blocklog.db"
prev_block = 0
checkepoch = ''

sendStream = 'if [ ! -e "send.txt" ]; then send=0; echo $send | tee send.txt; else cat send.txt; fi'
send = (subprocess.Popen(sendStream, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
send = int(send.strip())
line_leader_str_list = []

#多言語設定
i18n_path = pathlib.Path(__file__).parent.absolute() / "i18n"
i18n.load_path.append(i18n_path)
i18n.set('locale', notify_language)

#guild_db存在確認
guild_db_fullpath = guild_db_dir + guild_db_name
guild_db_is_file = os.path.isfile(guild_db_fullpath)
shelley_is_file = os.path.isfile(shelley_genesis)
byron_is_file = os.path.isfile(byron_genesis)

#ShelleyGenesis読み込み
with open(shelley_genesis) as fs:
    shgenesis = json.load(fs)
    
with open(byron_genesis) as fb:
    bygenesis = json.load(fb)
    
sh_active_slots_coeff = shgenesis['activeSlotsCoeff']
sh_epoch_length = shgenesis['epochLength']
byronk = bygenesis['protocolConsts']['k']

#通知基準
match notify_level:
    case "All":
        notStatus = ('adopted','leader')
    case "ExceptCofirm":
        notStatus = ('adopted','leader','confirmed')
    case "OnlyMissed":
        notStatus = ('adopted','leader','confirmed','ghosted','stolen')
        

def connect_db():
    connection = sqlite3.connect(guild_db_fullpath)
    cursor = connection.cursor()
    return connection, cursor

def sendMessage(b_message):
    match notify_platform:
        case "Line":
            d_line_notify(b_message)
        case "Discord":
            discord = Discord(url=discord_webhook_url)
            discord.post(content=b_message)
        case "Slack":
            slack = slackweb.Slack(url=slack_webhook_url)
            slack.notify(text=b_message)
        case "Telegram":
            send_text = 'https://api.telegram.org/bot' + telegram_token + '/sendMessage?chat_id=' + telegram_id + '&parse_mode=Markdown&text=' + b_message
            response = requests.get(send_text)
            response.json()


def getNo(slotEpoch,epochNo,cursor):
    ssNo = 0
    # try:
    #     connection, cursor = connect_db()
    #     #print("Connected to SQLite")
    getEpoch()
    sqlite_select_query = f"SELECT * FROM blocklog WHERE epoch=={epochNo} order by slot asc;"
    cursor.execute(sqlite_select_query)
    epoch_records = cursor.fetchall()
    #print(i18n.t('message.total_schedule') + ":", len(epoch_records))
    for i, row in enumerate(epoch_records, 1):
        if slotEpoch == row[5]:
            ssNo = i
            break
        #else:
            #ssNo = 0

    #     cursor.close()

    # except sqlite3.Error as error:
    #     print(i18n.t('message.st_db_failed_read'), error)
    # finally:
    #     if connection:
    #         connection.close()
    #         #print(i18n.t('message.st_closed_sql') + "\n")
    return ssNo, len(epoch_records)

def d_line_notify(line_message):

    line_notify_api = 'https://notify-api.line.me/api/notify'

    payload = {'message': line_message}
    headers = {'Authorization': 'Bearer ' + line_notify_token}  # 発行したトークン
    line_notify = requests.post(line_notify_api, data=payload, headers=headers)

def getEpoch():
    bepochNo = 0
    get_metrics = getEpochMetrics()
    checkepoch = len(get_metrics)
    if not checkepoch:
        print(i18n.t('message.st_wait_node_sync'))
    else:
        bepochNo = get_metrics.replace('cardano_node_metrics_epoch_int ', '')
        #print(i18n.t('message.epoch') + ":", bepochNo)
    return bepochNo

def getEpochMetrics():
    cmd = f'curl -s localhost:{prometheus_port}/metrics | grep epoch'
    process = (subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            shell=True).communicate()[0]).decode('utf-8')
    return process


def getAllRows(timing):
    try:
        global prev_block
        next_leader_records = "Null"
        connection, cursor = connect_db()
        #print(i18n.t('message.st_connected_sql'))

        sqlite_select_query = """SELECT * FROM blocklog WHERE status NOT IN ("adopted","leader") order by at desc limit 1;"""
        cursor.execute(sqlite_select_query)
        records = cursor.fetchall()

        #print("Total rows are:  ", len(records))
        #print("Printing each row")
        for row in records:
            
            #print(i18n.t('message.slot_no')+":", row[1])
        
            at_string = row[2]
            btime = parser.parse(at_string).astimezone(timezone(notify_timezone)).strftime('%Y-%m-%d %H:%M:%S')
            #print("at: ", btime)
            #print("epoch: ", row[3])
            #print("block: ", row[4])
            #print("slot_in_epoch: ", row[5])
            #print("status: ", row[8])
            #print("prevblock", prev_block)
            #print("\n")
            #スケジュール番号計算
            scheduleNo, total_schedule = getNo(row[5],row[3],cursor)

            sqlite_next_leader = f"SELECT * FROM blocklog WHERE slot >= {row[1]} order by slot asc limit 1 offset 1;"
            cursor.execute(sqlite_next_leader)
            next_leader_records = cursor.fetchall()

            #print(i18n.t('message.timezone')+":", notify_timezone)
            #print(i18n.t('message.next_schedule')+":", next_leader_records)
            if next_leader_records:
                for next_leader_row in next_leader_records:
                    at_next_string = next_leader_row[2]
                    next_btime = parser.parse(at_next_string).astimezone(timezone(notify_timezone))
                    p_next_btime = str(next_btime)

            else:
                next_leader_records = "Null"
                p_next_btime = i18n.t('message.st_getschedule_slot')
                print(i18n.t('message.next_schedule_at')+":", p_next_btime)

            if row[4] != "0":
                blockUrl=f"https://pooltool.io/realtime/{row[4]}\r\n"

            if timing == 'modified':
                if prev_block != row[4] and row[8] not in notStatus:
                    #LINE通知内容
                    b_message = '\r\n' + pool_ticker + ' ' + i18n.t('message.block_minted_result', current_epoch=str(row[3])) +'\r\n'\
                        + '\r\n'\
                        + '📍'+str(scheduleNo)+' / '+str(total_schedule)+' > '+ str(row[8])+'\r\n'\
                        + '⏰'+str(btime)+'\r\n'\
                        + '\r\n'\
                        + '📦' + i18n.t('message.block_no') + ":" + str(row[4]) + '\r\n'\
                        + '⏱' + i18n.t('message.slot_no') + ":" + str(row[1]) + ' (e:'+str(row[5]) + ')\r\n'\
                        + blockUrl\
                        + '\r\n'\
                        + i18n.t('message.next_schedule') + ' >>\r\n'\
                        + p_next_btime+'\r\n'\

                    sendMessage(b_message)
                    print(f"{str(btime)} - {str(row[4])} {str(scheduleNo)}/{str(total_schedule)} >> {str(row[8])}")
                    #通知先 LINE=0 Discord=1 Slack=2 Telegram=3 ※複数通知は不可

                else:
                    break
            else:
                prev_block = row[4]
                #print("prevblock", prev_block)

        if len(records) > 0:
            if row[8] not in ['adopted','leader']:
                prev_block = row[4]

    except sqlite3.Error as error:
        print("Failed to read data from table", error)
    else:
        if timing == 'start':
            start_message = '\r\n' + i18n.t('message.st_started_run', ticker=pool_ticker) + '🟢\r\n'\

            sendMessage(start_message)

            #Startup message
            run_title = '\n----------------------------------------------' \
                + '\n  ' + i18n.t('message.tool_title') + f" - Version:{version}\n" \
                + '----------------------------------------------' \

            print(run_title)
            print(i18n.t('message.next_schedule')+":", f"{next_leader_records}\n")
            print(i18n.t('message.st_started_run', ticker=pool_ticker) + "\n")
    finally:
        if connection:
            cursor.close()
            connection.close()


def getScheduleSlot():
    line_leader_str_list = []
    leader_str = ""
    
    slotComm = f'curl -s localhost:{prometheus_port}/metrics | grep slotNum_int | grep -o [0-9]*'
    slotn = (subprocess.Popen(slotComm, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
    
    slot_num = int(slotn.rstrip())
    
    slotIn_Comm = f'curl -s localhost:{prometheus_port}/metrics | grep slotIn | grep -o [0-9]*'
    slot_in = (subprocess.Popen(slotIn_Comm, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
    
    slot_in_epoch = int(slot_in.rstrip())
    
    global send

    next_slot_nonce = (slot_num - slot_in_epoch + sh_epoch_length) - (3 * byronk / sh_active_slots_coeff)
    next_slot_nonce = int(next_slot_nonce + 700)
    
    #print(slot_num,slot_in_epoch,sh_epoch_length,byronk,sh_active_slots_coeff)
    #print(next_slot_nonce)

    
    #スケジュールスロットエポック判定
    if slot_num > next_slot_nonce:
        #スケジュール送信有無確認
        if send == 0:
            currentEpoch = getEpoch()
            nextEpoch = int(currentEpoch) + 1
            #leaderlogサービス起動確認
            leadrlog_service_cmd = "ps aux | grep cnode-cncli-leaderlog.service | awk '{print $NF}'"
            leadrlog_seivice = (subprocess.Popen(leadrlog_service_cmd, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
            if leadrlog_seivice:
                #起動中
                #DB次スケジュール確認
                connection, cursor = connect_db()
                while True:
                    try:
                        sqlite_epochdata_query = f"SELECT * FROM epochdata WHERE epoch=={nextEpoch};"
                        cursor.execute(sqlite_epochdata_query)
                        epochdata_records = cursor.fetchone()
                        if epochdata_records:  #次エポックデータがあった場合
                            luck = epochdata_records[7]
                            ideal = epochdata_records[6]

                            next_epoch_leader = f"select * from blocklog where epoch = {nextEpoch} order by slot asc;"
                            cursor.execute(next_epoch_leader)
                            fetch_leader_records = cursor.fetchall()
                            if (len(fetch_leader_records) != 0):
                                line_count = 1
                                line_leader_str = ""
                                
                                #スケジュール日付通知
                                if nextepoch_leader_date == "SummaryDate":
                                    for x, next_epoch_leader_row in enumerate(fetch_leader_records, 1):

                                        at_leader_string = next_epoch_leader_row[2]
                                        leader_btime = parser.parse(at_leader_string).astimezone(timezone(notify_timezone)).strftime('%Y-%m-%d %H:%M:%S')
                                        #LINE対策 20スケジュールごとに分割
                                        if notify_platform == "Line" and x >= 21:
                                            if line_count <= 20:

                                                line_leader_str += f"{x}) {next_epoch_leader_row[5]} / {leader_btime}\n"
                                                line_count += 1
                                                if line_count == 21 or x == len(fetch_leader_records):
                                                    line_leader_str_list.append(line_leader_str)
                                                    line_leader_str = ""
                                                    line_count = 1

                                        else:
                                            leader_str += f"{x}) {next_epoch_leader_row[5]} / {leader_btime}\n"

                                        #p_leader_btime = str(leader_btime)
                                else:
                                    leader_str = i18n.t('message.st_nextepoch_leader_date')

                                b_message = '\r\n\r\n' + i18n.t('message.epoch_schedule_details', ticker=pool_ticker, nextEpoch=str(nextEpoch)) + '\r\n'\
                                    + '📈' + i18n.t('message.ideal') + '    :' + str(ideal) + '\r\n'\
                                    + '💎' + i18n.t('message.luck') + ' :' + str(luck) + '%\r\n'\
                                    + '📋' + i18n.t('message.allocated_blocks') + ' : ' + str(len(fetch_leader_records))+'\r\n'\
                                    + '\r\n'\
                                    + leader_str + '\r\n'\

                            else:  #次エポックスケジュールがなかった場合
                                b_message = '\r\n' + i18n.t('message.epoch_schedule_details', ticker=pool_ticker, nextEpoch=str(nextEpoch)) + '\r\n'\
                                    + i18n.t('message.st_not_schedule') + '\r\n'\

                            sendMessage(b_message)

                            
                            if nextepoch_leader_date == "SummaryDate":
                                #LINE対応
                                line_index = 0
                                len_line_list = len(line_leader_str_list)

                                if notify_platform == "Line":
                                    while line_index < len_line_list:
                                        b_message = '\r\n' + line_leader_str_list[line_index] + '\r\n'\

                                        sendMessage(b_message)
                                        line_index += 1


                            send = 1
                            stream = os.popen(f'send={send}; echo $send > send.txt')
                            break
                        else:
                            #次エポックスケジュールがなかった場合
                            print(i18n.t('message.st_nextepoch_leader_refetch'))
                            time.sleep(60)
                            
                    except sqlite3.Error as error:
                        print(i18n.t('message.st_db_failed_read'), error)
                        break

                if connection:
                    cursor.close()
                    connection.close()
                
            else:
                #起動していない
                #スケジュール取得可能メッセージ送信
                b_message = '\r\n' + i18n.t('message.notification', ticker=pool_ticker) + '📣\r\n'\
                    + i18n.t('message.st_passed_the_slot', currentEpoch=str(currentEpoch.strip()), slotn=str(slotn)) + '\r\n'\
                    + i18n.t('message.st_you_canget_theschedule', nextepoch=str(nextEpoch)) + '\r\n'\

                sendMessage(b_message)
                send = 1
                stream = os.popen(f'send={send}; echo $send > send.txt')
    else:
        if send == 1:
            send = 0
            stream = os.popen(f'send={send}; echo $send > send.txt')


class MyFileWatchHandler(PatternMatchingEventHandler):

    # ファイル変更時の動作
    def on_modified(self, event):
        filepath = event.src_path
        filename = os.path.basename(filepath)
        #print(filepath)
        #print(filename)
        dt_now = datetime.datetime.now()
        fsize = os.path.getsize(filepath)
        if filename.startswith('block'):
            #print(f"{dt_now} {filename}")
            #print(f"-- size: {fsize}")
            timing = 'modified'
            getAllRows(timing)


if __name__ == "__main__":
    args = sys.argv
    if len(args) == 1:
        # 対象ディレクトリ
        DIR_WATCH = guild_db_dir
        #print(DIR_WATCH)
        # 対象ファイルパスのパターン
        PATTERNS = [guild_db_name]

        try:
            pytz.timezone(notify_timezone)
        except pytz.UnknownTimeZoneError:
            print(notify_timezone + ":" + i18n.t('message.st_notfound_timezone'))
            sys.exit()

        if notify_platform not in ('Line','Discord','Slack','Telegram'):
            print(i18n.t('message.st_setting_alert_flag'))
        elif not guild_db_is_file:
            print(i18n.t('message.st_guilddb_file'))
        elif not shelley_is_file:
            print(i18n.t('message.st_shelley_genesis_file'))
        elif not byron_is_file:
            print(i18n.t('message.st_byron_genesis_file'))
        elif not pool_ticker:
            print(i18n.t('message.st_notfound_ticker'))
        elif notify_language not in ('en','ja'):
            print("Set your notification language.")
        elif nextepoch_leader_date not in ('SummaryOnly','SummaryDate'):
            print(i18n.t('message.st_notfound_nextepoch_notifylevel'))
        elif notify_level not in ('All','ExceptCofirm','OnlyMissed'):
            print(i18n.t('message.st_setting_alert_flag'))
        else:
            if notify_platform == "Line" and line_notify_token == "":
                print(i18n.t('message.st_line_token'))
            elif notify_platform == "Discord" and discord_webhook_url == "":
                print(i18n.t('message.st_webhook_url'))
            elif notify_platform == "Slack" and slack_webhook_url == "":
                print(i18n.t('message.st_webhook_url'))
            elif notify_platform == "Telegram" and telegram_token == "":
                print(i18n.t('message.st_telegram_token'))
            else:
                while True:
                    checkepoch = len(getEpochMetrics())
                    if not checkepoch:
                        print(i18n.t('message.st_wait_node_sync'))
                        time.sleep(10)
                    else:
                        print(i18n.t('message.st_done_node_sync'))
                        break
                 
                event_handler = MyFileWatchHandler(patterns=PATTERNS)
                observer = Observer()
                observer.schedule(event_handler, DIR_WATCH, recursive=True)
                observer.start()
                observer.is_alive()
                timing = 'start'
                
                getAllRows(timing)
                
                try:
                    while True:
                        time.sleep(1)
                        getScheduleSlot()
                except KeyboardInterrupt:
                    observer.stop()
                observer.join()
    elif len(args) == 2 and args[1] == 'V' or len(args) == 2 and args[1] == 'version':
        print(f"v{version}")
    else:
        print(i18n.t('message.sy_invalid_optional_argument'))
