#2023/12/19 v2.0.0 @btbf

from watchdog.events import RegexMatchingEventHandler
from watchdog.observers import Observer
from concurrent.futures import ThreadPoolExecutor
import os
import time
import datetime
import sqlite3
import requests
import slackweb
import subprocess
import random
import i18n
from pytz import timezone
from dateutil import parser
from discordwebhook import Discord
from dotenv import load_dotenv

i18n.load_path.append('./i18n')
i18n.set('locale', 'ja')

# .envファイルの内容を読み込みます
load_dotenv()

# 環境変数を読み込む
guild_db_dir = os.environ["guild_db_dir"]
usrhome = os.environ["HOME"]
home = os.environ["NODE_HOME"]
ticker = os.environ["ticker"]
line_notify_token = os.environ["line_notify_token"]
dc_notify_url = os.environ["dc_notify_url"]
b_timezone = os.environ["b_timezone"]
bNotify = os.environ["bNotify"]
bNotify_st = os.environ["bNotify_st"]
slack_notify_url = os.environ["slack_notify_url"]
teleg_token = os.environ["teleg_token"]
teleg_id = os.environ["teleg_id"]
auto_leader = os.environ["auto_leader"]
#s_No = 1
prev_block = 0
sendStream = 'if [ ! -e "send.txt" ]; then send=0; echo $send | tee send.txt; else cat send.txt; fi'
send = (subprocess.Popen(sendStream, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
send = int(send.strip())
line_leader_str_list = []

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


def getAllRows(timing):
    try:
        global prev_block
        connection = sqlite3.connect(usrhome + guild_db_dir + 'blocklog.db')
        cursor = connection.cursor()
        print(i18n.t('message.sentence_connected_sql'))

        sqlite_select_query = """SELECT * FROM blocklog WHERE status NOT IN ("adopted","leader") order by at desc limit 1;"""
        cursor.execute(sqlite_select_query)
        records = cursor.fetchall()

        #print("Total rows are:  ", len(records))
        #print("Printing each row")
        for row in records:
            
            print(i18n.t('message.slot_no')+":", row[1])
        
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

            print(i18n.t('message.timezone')+":", b_timezone)
            print(i18n.t('message.next_schedule')+":", next_leader_records)
            if next_leader_records:
                for next_leader_row in next_leader_records:
                    at_next_string = next_leader_row[2]
                    next_btime = parser.parse(at_next_string).astimezone(timezone(b_timezone))
                    print(i18n.t('message.getschedule_slot')+":", f"{random_slot_num}\n")
                    p_next_btime = str(next_btime)

            else:
                p_next_btime = i18n.t('message.sentence_getschedule_slot')
                print(i18n.t('message.next_schedule_at')+":", p_next_btime)

            if row[4] != "0":
                blockUrl=f"https://pooltool.io/realtime/{row[4]}\r\n"

            if timing == 'modified':
                if prev_block != row[4] and row[8] not in notStatus:
                    #LINE通知内容
                    b_message = '\r\n' + ticker + i18n.t('message.getschedule_slot', current_epoch=str(row[3])) +'\r\n'\
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
                print(i18n.t('message.sentence_started_tool'))
                start_message = '\r\n' + i18n.t('message.sentence_started_run', ticker=ticker) + '🟢\r\n'\
                    + i18n.t('message.sentence_schedule_slot', get_slot=str(random_slot_num)) +'\r\n'\

                sendMessage(start_message)

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
        connection = sqlite3.connect(home + '/guild-db/blocklog/blocklog.db')
        cursor = connection.cursor()
        #print("Connected to SQLite")
        getEpoch()
        sqlite_select_query = f"SELECT * FROM blocklog WHERE epoch=={epochNo} order by slot asc;"
        cursor.execute(sqlite_select_query)
        epoch_records = cursor.fetchall()
        print(i18n.t('message.total_schedule') + ":", len(epoch_records))
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
            print(i18n.t('message.sentence_closed_sql') + "\n")
            return ssNo, len(epoch_records)

def d_line_notify(line_message):

    line_notify_api = 'https://notify-api.line.me/api/notify'

    payload = {'message': line_message}
    headers = {'Authorization': 'Bearer ' + line_notify_token}  # 発行したトークン
    line_notify = requests.post(line_notify_api, data=payload, headers=headers)

def getEpoch():
    #subprocess.call('curl -s localhost:12798/metrics | grep epoch')
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
            print (i18n.t('message.epoch') + ":", bepochNo)
            break
        time.sleep(30)
    return bepochNo

def randomSlot():
    random_slot=random.randrange(303300, 317700, 120)
    return random_slot

def getScheduleSlot():
    line_leader_str_list = []
    leader_str = ""
    #slotComm = os.popen('curl -s localhost:12798/metrics | grep slotIn | grep -o [0-9]*')
    slotComm = "curl -s localhost:12798/metrics | grep slotIn | grep -o [0-9]*"
    #slotn = slotComm.read()
    slotn = (subprocess.Popen(slotComm, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
    slotn = int(slotn)
    global send

    if (slotn >= random_slot_num):
        if send == 0:
            currentEpoch = getEpoch()
            nextEpoch = int(currentEpoch) + 1
            if auto_leader == "1":
                subprocess.Popen("tmux send-keys -t leaderlog '$NODE_HOME/scripts/cncli.sh leaderlog' C-m" , shell=True)
                b_message = '\r\n' + i18n.t('message.notification', ticker=ticker) + '📣\r\n'\
                    + i18n.t('message.sentence_you_canget_theschedule', nextepoch=str(nextEpoch)) + '\r\n'\
                    + i18n.t('message.sentence_alert_min_schedule')\

            else:
                b_message = '\r\n' + i18n.t('message.notification', ticker=ticker) + '📣\r\n'\
                    + i18n.t('message.sentence_passed_the_slot', currentEpoch=str(currentEpoch.strip()), slotn=str(slotn)) + '\r\n'\
                    + i18n.t('message.sentence_you_canget_theschedule', nextepoch=str(nextEpoch)) + '\r\n'\

            sendMessage(b_message)
            #print ("スケジュールが取得できます")
            send = 1
            stream = os.popen(f'send={send}; echo $send > send.txt')
        elif send >= 1 and send <= 5: #スケジュール結果送信
            currentEpoch = getEpoch()
            nextEpoch = int(currentEpoch) + 1
            try:
                connection = sqlite3.connect(home + '/guild-db/blocklog/blocklog.db')
                cursor = connection.cursor()
                print(i18n.t('message.sentence_connected_sql'))

                sqlite_epochdata_query = f"select * from epochdata where epoch = {nextEpoch} LIMIT 1;"
                cursor.execute(sqlite_epochdata_query)
                fetch_epoch_records = cursor.fetchall()
                next_epoch_records = len(fetch_epoch_records)

                if (next_epoch_records == 1 and send == 5):
                    for fetch_epoch_row in fetch_epoch_records:
                        luck = fetch_epoch_row[7]
                        ideal = fetch_epoch_row[6]

                    #print("エポックレコードあり")
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

                    else:
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

                    send += 1
                    stream = os.popen(f'send={send}; echo $send > send.txt')
                elif (next_epoch_records == 1 and send < 5):
                    send += 1
                    stream = os.popen(f'send={send}; echo $send > send.txt')
                else:
                    pass

                cursor.close()

            except sqlite3.Error as error:
                print(i18n.t('message.sentence_db_failed_read'), error)
            finally:
                if connection:
                    connection.close()
                    print(i18n.t('message.sentence_closed_sql') + '\n')

        else:
            pass
            #print(send)

    else:
        if send >= 1:
            send = 0
            stream = os.popen(f'send={send}; echo $send > send.txt')


class MyFileWatchHandler(RegexMatchingEventHandler):

    def __init__(self, regexes):
        super().__init__(regexes=regexes)

    # ファイル変更時の動作
    def on_modified(self, event):
        filepath = event.src_path
        filename = os.path.basename(filepath)
        dt_now = datetime.datetime.now()
        fsize = os.path.getsize(filepath)
        if filename.startswith('block'):
            print(f"{dt_now} {filename}")
            print(f"-- size: {fsize}")
            timing = 'modified'
            getAllRows(timing)


random_slot_num=randomSlot()

if __name__ == "__main__":

    # 対象ディレクトリ
    DIR_WATCH = usrhome + guild_db_dir
    # 対象ファイルパスのパターン
    PATTERNS = [r'^.\/blocklog.*\.db$']

    def on_modified(event):
        filepath = event.src_path
        filename = os.path.basename(filepath)
        print('%s changed' % filename)

    if bNotify >= "4" or bNotify == "":
        print(i18n.t('message.sentence_setting_alert_flag'))
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
            timeslot = 1
            try:
                while True:
                    time.sleep(1)
                    if timeslot == 5:
                        getScheduleSlot()
                        timeslot = 0
                    timeslot += 1

            except KeyboardInterrupt:
                observer.stop()
            observer.join()