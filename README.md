# SPO Block Notify

Notify block mint results to any message platform.

## Setup

<details>

<summary>English Ver.</summary>

### 0.Prerequisites
- It is necessary to set up cncli.sh developed by the guild operator in advance.
[https://cardano-community.github.io/guild-operators/Scripts/cncli/](https://cardano-community.github.io/guild-operators/Scripts/cncli/)

- This program must be installed on the server where cncli.sh and the accompanying CNCLI blocklog are set up.

### 1.Install Dependent Programs

Check python version
```bash
python3 -V
```
> Over Python 3.8.10

Update Package
```bash
sudo apt update -y
```

```bash
sudo apt install -y python3-watchdog python3-tz python3-dateutil python3-requests build-essential libssl-dev libffi-dev python3-dev python3-pip
```
```bash
pip install discordwebhook python-dotenv slackweb i18nice
```

### **Download scripts and configuration files**
```
cd $NODE_HOME/scripts
git clone https://github.com/btbf/block-notify.git
cd block-notify
git fetch --all --recurse-submodules --tags
git checkout tags/<latest_tag_name>
chmod 755 block_check.py
```


### 2. Usage

Editing Configuration Files

```
nano .env
```

| 項目      | 使用用途                          |
| ----------- | ------------------------------------ |
| `guild_db_dir`       | Path of the blocklog.db directory  |
| `guild_db_name`       | File name of block log DB  |
| `ticker`       | Pool ticker name  |
| `line_notify_token`      | Line Notify Token |
| `dc_notify_url`    | Discord Webhook URL |
| `slack_notify_url`    | Slack Webhook URL |
| `teleg_token`    | Telegram API Token |
| `teleg_id`    | Telegram ChatID |
| `language`    | used language |
| `b_timezone`    | Time Zone |
| `bNotify`    | notify in advance |
| `bNotify_st`    | Notification benchmarks |
| `auto_leader`    | How to obtain a schedule |

</details>

<details>

<summary>日本語 Ver.</summary>

### 0.前提条件

- 事前にギルドオペレータが開発したcncli.shのセットアップが必要です。
[https://cardano-community.github.io/guild-operators/Scripts/cncli/](https://cardano-community.github.io/guild-operators/Scripts/cncli/)

- このプログラムはcncli.shと付随するCNCLI blocklogがセットアップされたサーバーへインストールする必要があります。

### 1.依存プログラムをインストールする

pythonバージョンを確認する
```bash
python3 -V
```
> Python 3.8.10以上 

パッケージを更新する
```bash
sudo apt update -y
```

```bash
sudo apt install -y python3-watchdog python3-tz python3-dateutil python3-requests build-essential libssl-dev libffi-dev python3-dev python3-pip
```
```bash
pip install discordwebhook python-dotenv slackweb i18nice
```

### **スクリプトと設定ファイルをダウンロードする**
```
cd $NODE_HOME/scripts
git clone https://github.com/btbf/block-notify.git
cd block-notify
git fetch --all --recurse-submodules --tags
git checkout tags/<latest_tag_name>
chmod 755 block_check.py
```

### 使い方

設定ファイルの編集

```
nano .env
```

| 項目      | 使用用途                          |
| ----------- | ------------------------------------ |
| `guild_db_dir`       | blocklog.dbディレクトリのパス  |
| `guild_db_name`       | ブロックログDBのファイル名  |
| `ticker`       | プールティッカー名  |
| `line_notify_token`      | Line Notifyトークン |
| `dc_notify_url`    | DiscordウェブフックURL |
| `slack_notify_url`    | SlackウェブフックURL |
| `teleg_token`    | Telegram APIトークン |
| `teleg_id`    | Telegram ChatID |
| `language`    | 使用言語 |
| `b_timezone`    | お住いのタイムゾーン指定 |
| `bNotify`    | 通知先指定 |
| `bNotify_st`    | 通知基準 |
| `auto_leader`    | スケジュール取得方法 |

</details>