#2024/1/19 v2.0.0 @btbf
version = "2.1.0"

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
from concurrent.futures import ThreadPoolExecutor
from os.path import dirname
import os
import time
import datetime
import sqlite3
import requests
import slackweb
import subprocess
import random
import i18n
import json
from pytz import timezone
from dateutil import parser
from discordwebhook import Discord
from dotenv import load_dotenv

# .envファイルの内容を読み込みます
dotenv_path = f"{dirname(__file__)}/.env2"
load_dotenv(dotenv_path)

# 環境変数を読み込む
guild_db_dir = os.environ["guild_db_dir"]
shelley_genesis = os.environ["shelley_genesis"]
byron_genesis = os.environ["byron_genesis"]
home = os.environ["NODE_HOME"]
ticker = os.environ["ticker"]
line_notify_token = os.environ["line_notify_token"]
dc_notify_url = os.environ["dc_notify_url"]
language = os.environ["language"]
b_timezone = os.environ["b_timezone"]
bNotify = os.environ["bNotify"]
bNotify_st = os.environ["bNotify_st"]
slack_notify_url = os.environ["slack_notify_url"]
teleg_token = os.environ["teleg_token"]
teleg_id = os.environ["teleg_id"]
guild_db_name = "blocklog.db"
#s_No = 1
prev_block = 0
schedule_get_slot = 304200

sendStream = 'if [ ! -e "send.txt" ]; then send=0; echo $send | tee send.txt; else cat send.txt; fi'
send = (subprocess.Popen(sendStream, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
send = int(send.strip())
line_leader_str_list = []

#多言語設定
i18n.load_path.append('./i18n')
i18n.set('locale', language)

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



#print(send)

#通知基準 全て=0 confirm以外全て=1 Missedとivaildのみ=2
if bNotify_st == "0":
    notStatus = ['adopted','leader']
elif bNotify_st == "1":
    notStatus = ['adopted','leader','confirmed']
elif bNotify_st == "2":
    notStatus = ['adopted','leader','confirmed','ghosted','stolen']
else:
    print(i18n.t('message.sentence_setting_alert_flag'))


def connect_db():
    connection = sqlite3.connect(guild_db_fullpath)
    cursor = connection.cursor()
    return connection, cursor


def getAllRows(timing):
    try:
        global prev_block
        connection, cursor = connect_db()
        #print(i18n.t('message.sentence_connected_sql'))

        sqlite_select_query = """SELECT * FROM blocklog WHERE status NOT IN ("adopted","leader") order by at desc limit 1;"""
        cursor.execute(sqlite_select_query)
        records = cursor.fetchall()

        #print("Total rows are:  ", len(records))
        #print("Printing each row")
        for row in records:
            
            #print(i18n.t('message.slot_no')+":", row[1])
        
            at_string = row[2]
            btime = parser.parse(at_string).astimezone(timezone(b_timezone)).strftime('%Y-%m-%d %H:%M:%S')
            #print("at: ", btime)
            #print("epoch: ", row[3])
            #print("block: ", row[4])
            #print("slot_in_epoch: ", row[5])
            #print("status: ", row[8])
            #print("prevblock", prev_block)
            #print("\n")
            #スケジュール番号計算
            scheduleNo, total_schedule = getNo(row[5],row[3])

            sqlite_next_leader = f"SELECT * FROM blocklog WHERE slot >= {row[1]} order by slot asc limit 1 offset 1;"
            cursor.execute(sqlite_next_leader)
            next_leader_records = cursor.fetchall()

            #print(i18n.t('message.timezone')+":", b_timezone)
            #print(i18n.t('message.next_schedule')+":", next_leader_records)
            if next_leader_records:
                for next_leader_row in next_leader_records:
                    at_next_string = next_leader_row[2]
                    next_btime = parser.parse(at_next_string).astimezone(timezone(b_timezone))
                    #print(i18n.t('message.getschedule_slot')+":", f"{random_slot_num}\n")
                    p_next_btime = str(next_btime)

            else:
                p_next_btime = i18n.t('message.sentence_getschedule_slot')
                print(i18n.t('message.next_schedule_at')+":", p_next_btime)

            if row[4] != "0":
                blockUrl=f"https://pooltool.io/realtime/{row[4]}\r\n"

            if timing == 'modified':
                if prev_block != row[4] and row[8] not in notStatus:
                    #LINE通知内容
                    b_message = '\r\n' + ticker + ' ' + i18n.t('message.block_minted_result', current_epoch=str(row[3])) +'\r\n'\
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

        cursor.close()

    except sqlite3.Error as error:
        print("Failed to read data from table", error)
    finally:
        if connection:
            connection.close()
            if timing == 'start':
                start_message = '\r\n' + i18n.t('message.sentence_started_run', ticker=ticker) + '🟢\r\n'\

                sendMessage(start_message)
                
                #Startup message
                run_title = '\n----------------------------------------------' \
                    + '\n  ' + i18n.t('message.tool_title') + f"   -    Ver:{version}\n" \
                    + '----------------------------------------------' \
                    
                print(run_title)
                #print(i18n.t('message.getschedule_slot')+":", f"{random_slot_num}\n")
                print(i18n.t('message.next_schedule')+":", f"{next_leader_records}\n")
                print(i18n.t('message.sentence_started_run', ticker=ticker) + "\n")


def sendMessage(b_message):
    #通知先 LINE=0 Discord=1 Slack=2 Telegram=3 ※複数通知は不可
    if bNotify == "0":
        d_line_notify(b_message)
    elif bNotify == "1":
        discord = Discord(url=dc_notify_url)
        discord.post(content=b_message)
    elif bNotify == "2":
        slack = slackweb.Slack(url=slack_notify_url)
        slack.notify(text=b_message)
    else:
        send_text = 'https://api.telegram.org/bot' + teleg_token + '/sendMessage?chat_id=' + teleg_id + '&parse_mode=Markdown&text=' + b_message
        response = requests.get(send_text)
        response.json()


def getNo(slotEpoch,epochNo):
    ssNo = 0
    try:
        connection, cursor = connect_db()
        #print("Connected to SQLite")
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

        cursor.close()

    except sqlite3.Error as error:
        print(i18n.t('message.sentence_db_failed_read'), error)
    finally:
        if connection:
            connection.close()
            #print(i18n.t('message.sentence_closed_sql') + "\n")
            return ssNo, len(epoch_records)

def d_line_notify(line_message):

    line_notify_api = 'https://notify-api.line.me/api/notify'

    payload = {'message': line_message}
    headers = {'Authorization': 'Bearer ' + line_notify_token}  # 発行したトークン
    line_notify = requests.post(line_notify_api, data=payload, headers=headers)

def getEpoch():

    bepochNo = 0
    while True:
        cmd = 'curl -s localhost:12798/metrics | grep epoch'
        process = (subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
        checkepoch = len(process)
        if checkepoch == 0:
            print (i18n.t('message.sentence_wait_node_sync'))

        else:
            bepochNo = process.replace('cardano_node_metrics_epoch_int ', '')
            #print (i18n.t('message.epoch') + ":", bepochNo)
            break
        time.sleep(30)
    return bepochNo


def getScheduleSlot():
    line_leader_str_list = []
    leader_str = ""
    
    slotComm = "curl -s localhost:12798/metrics | grep slotNum_int | grep -o [0-9]*"
    slotn = (subprocess.Popen(slotComm, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
    slot_num = int(slotn)
    
    slotIn_Comm = "curl -s localhost:12798/metrics | grep slotIn | grep -o [0-9]*"
    slot_in = (subprocess.Popen(slotIn_Comm, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
    slot_in_epoch = int(slot_in)
    
    global send

    next_slot_nonce = (slot_num - slot_in_epoch + sh_epoch_length) - (3 * byronk / sh_active_slots_coeff)
    next_slot_nonce = int(next_slot_nonce + 600)
    
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
                                for x, next_epoch_leader_row in enumerate(fetch_leader_records, 1):

                                    at_leader_string = next_epoch_leader_row[2]
                                    leader_btime = parser.parse(at_leader_string).astimezone(timezone(b_timezone)).strftime('%Y-%m-%d %H:%M:%S')
                                    #LINE対策 20スケジュールごとに分割
                                    if bNotify == "0" and x >= 21:
                                        if line_count <= 20:

                                            line_leader_str += f"{x}) {next_epoch_leader_row[5]} / {leader_btime}\n"
                                            line_count += 1
                                            if line_count == 21 or x == len(fetch_leader_records):
                                                line_leader_str_list.append(line_leader_str)
                                                line_leader_str = ""
                                                line_count = 1

                                    else:
                                        leader_str += f"{x}) {next_epoch_leader_row[5]} / {leader_btime}\n"

                                    p_leader_btime = str(leader_btime)

                                b_message = '\r\n\r\n' + i18n.t('message.epoch_schedule_details', ticker=ticker, nextEpoch=str(nextEpoch)) + '\r\n'\
                                    + '📈' + i18n.t('message.ideal') + '    :' + str(ideal) + '\r\n'\
                                    + '💎' + i18n.t('message.luck') + ' :' + str(luck) + '%\r\n'\
                                    + '📋' + i18n.t('message.allocated_blocks') + ' : ' + str(len(fetch_leader_records))+'\r\n'\
                                    + '\r\n'\
                                    + leader_str + '\r\n'\

                            else:  #次エポックデータがなかった場合
                                b_message = '\r\n' + i18n.t('message.epoch_schedule_details', ticker=ticker, nextEpoch=str(nextEpoch)) + '\r\n'\
                                    + i18n.t('message.sentence_not_schedule') + '\r\n'\

                            sendMessage(b_message)

                            #LINE対応
                            line_index = 0
                            len_line_list = len(line_leader_str_list)

                            if bNotify == "0":
                                while line_index < len_line_list:
                                    b_message = '\r\n' + line_leader_str_list[line_index] + '\r\n'\

                                    sendMessage(b_message)
                                    line_index += 1


                            send = 1
                            stream = os.popen(f'send={send}; echo $send > send.txt')
                            cursor.close()
                            break
                        else:
                            #次エポックデータがなかった場合
                            print("エポックデータを再取得します")
                            time.sleep(60)
                            
                    except sqlite3.Error as error:
                        print(i18n.t('message.sentence_db_failed_read'), error)
                    finally:
                        if connection:
                            connection.close()
                
            else:
                #起動していない
                #スケジュール取得可能メッセージ送信
                b_message = '\r\n' + i18n.t('message.notification', ticker=ticker) + '📣\r\n'\
                    + i18n.t('message.sentence_passed_the_slot', currentEpoch=str(currentEpoch.strip()), slotn=str(slotn)) + '\r\n'\
                    + i18n.t('message.sentence_you_canget_theschedule', nextepoch=str(nextEpoch)) + '\r\n'\

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
        #print(filename)
        dt_now = datetime.datetime.now()
        fsize = os.path.getsize(filepath)
        if filename.startswith('block'):
            #print(f"{dt_now} {filename}")
            #print(f"-- size: {fsize}")
            timing = 'modified'
            getAllRows(timing)


if __name__ == "__main__":
    # 対象ディレクトリ
    DIR_WATCH = guild_db_dir
    #print(DIR_WATCH)
    # 対象ファイルパスのパターン
    PATTERNS = [guild_db_name]

    def on_modified(event):
        filepath = event.src_path
        filename = os.path.basename(filepath)
        print('%s changed' % filename)
    
    

    if bNotify >= "4" or bNotify == "":
        print(i18n.t('message.sentence_setting_alert_flag'))
    elif not guild_db_is_file:
        print(i18n.t('message.sentence_guilddb_file'))
    elif not shelley_is_file:
        print(i18n.t('message.sentence_shelley_genesis_file'))
    elif not byron_is_file:
        print(i18n.t('message.sentence_byron_genesis_file'))
    else:
        if bNotify == "0" and line_notify_token == "":
            print(i18n.t('message.sentence_line_token'))
        elif bNotify == "1" and dc_notify_url == "":
            print(i18n.t('message.sentence_webhook_url'))
        elif bNotify == "2" and slack_notify_url == "":
            print(i18n.t('message.sentence_webhook_url'))
        elif bNotify == "3" and teleg_token == "":
            print(i18n.t('message.sentence_telegram_token'))
        else:
            event_handler = MyFileWatchHandler(PATTERNS)
            observer = Observer()
            observer.schedule(event_handler, DIR_WATCH, recursive=True)
            observer.start()
            timing = 'start'

            getAllRows(timing)
            #timeslot = 1
            try:
                while True:
                    time.sleep(1)
                    #if timeslot == 5:
                    getScheduleSlot()
                    #    timeslot = 0
                    #timeslot += 1

            except KeyboardInterrupt:
                observer.stop()
            observer.join()