# SPO Block Notify

Notify block mint results to any message platform.

## Supported platforms
[LINE](https://notify-bot.line.me/ja/) / [Discord](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) / [Slack](https://api.slack.com/messaging/webhooks) / [Telegram](https://core.telegram.org/bots/api)

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
bn_release="$(curl -s https://api.github.com/repos/btbf/block-notify/releases/latest | jq -r '.tag_name')"
wget https://github.com/btbf/block-notify/archive/refs/tags/${bn_release}.tar.gz -P $NODE_HOME/scripts
cd $NODE_HOME/scripts
tar zxvf ${bn_release}.tar.gz block-notify-${bn_release}/block_notify.py block-notify-${bn_release}/.env block-notify-${bn_release}/i18n/
mv block-notify-${bn_release} block-notify
cd block-notify
```

### 2. Usage

Editing Configuration Files(.env)

```
nano .env
```

| 項目      | 使用用途                          |
| ----------- | ------------------------------------ |
| `guild_db_dir` | guild-dbのパスを入力する |
| `shelley_genesis` | shelley_genesisのファイルパスを入力する |
| `byron_genesis` | byron_genesisのファイルパスを入力する |
| `language` | 通知言語を入力する
| `ticker`       | プールティッカー名を入力する  |
| `line_notify_token`      | Line Notifyトークンを入力する |
| `dc_notify_url`    | DiscordウェブフックURLを入力する |
| `slack_notify_url`    | SlackウェブフックURLを入力する |
| `teleg_token`    | Telegram APIトークンを入力する |
| `teleg_id`    | Telegram ChatIDを入力する |
| `b_timezone`    | お住いのタイムゾーンを指定する |
| `bNotify`    | 通知先を指定する |
| `bNotify_st`    | 通知基準を設定する |
| `nextepoch_leader_date`    | #次エポックスケジュール日時の通知有無 |

**Configure the service file**

```bash
cat > $NODE_HOME/service/cnode-blocknotify.service << EOF 
# file: /etc/systemd/system/cnode-blocknotify.service

[Unit]
Description=Cardano Node - SPO Blocknotify
BindsTo=cnode-cncli-sync.service
After=cnode-cncli-sync.service

[Service]
Type=simple
RemainAfterExit=yes
Restart=on-failure
RestartSec=20
User=$(whoami)
WorkingDirectory=${NODE_HOME}/scripts
Environment="NODE_HOME=${NODE_HOME}"
ExecStart=/bin/bash -c 'cd ${NODE_HOME}/scripts/block-notify/ && python3 -u ./block_notify.py'
StandardInput=tty-force
SuccessExitStatus=143
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=cnode-blocknotify
TimeoutStopSec=5
KillMode=mixed

[Install]
WantedBy=cnode-cncli-sync.service
EOF
```

```
sudo cp $NODE_HOME/service/cnode-blocknotify.service /etc/systemd/system/cnode-blocknotify.service
```

```
sudo chmod 644 /etc/systemd/system/cnode-blocknotify.service
sudo systemctl daemon-reload
sudo systemctl enable cnode-blocknotify.service
```

Activate SPO BlockNotify
```
sudo systemctl start cnode-blocknotify.service
```

Add an alias for checking logs to the environment variable
```
echo alias blocknotify='"journalctl --no-hostname -u cnode-blocknotify -f"' >> $HOME/.bashrc
```

Environment variable reloading
```
source $HOME/.bashrc
```

Startup Confirmation
```
blocknotify
```

The following indications are fine.
> [xxx] SPO Block Notify has been started.

</details>

<details>

<summary>日本語 Ver.</summary>

### 0.前提条件

- 事前にギルドオペレータが開発したcncli.shのセットアップが必要です。
[https://cardano-community.github.io/guild-operators/Scripts/cncli/](https://cardano-community.github.io/guild-operators/Scripts/cncli/)

- このプログラムはcncli.shと付随するCNCLI blocklogがセットアップされたサーバーへインストールする必要があります。

- SPO JAPAN GUILDマニュアルを使用している場合は、こちらの[セットアップガイド](https://docs.spojapanguild.net/setup/11-blocknotify-setup/)をご参照ください。

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
bn_release="$(curl -s https://api.github.com/repos/btbf/block-notify/releases/latest | jq -r '.tag_name')"
wget https://github.com/btbf/block-notify/archive/refs/tags/${bn_release}.tar.gz -P $NODE_HOME/scripts
cd $NODE_HOME/scripts
tar zxvf ${bn_release}.tar.gz block-notify-${bn_release}/block_notify.py block-notify-${bn_release}/.env block-notify-${bn_release}/i18n/
mv block-notify-${bn_release} block-notify
cd block-notify
```

### 使い方

設定ファイルの編集

```
nano .env
```

| 項目      | 使用用途                          |
| ----------- | ------------------------------------ |
| `guild_db_dir` | guild-dbのパスを入力する |
| `shelley_genesis` | shelley_genesisのファイルパスを入力する |
| `byron_genesis` | byron_genesisのファイルパスを入力する |
| `language` | 通知言語を入力する
| `ticker`       | プールティッカー名を入力する  |
| `line_notify_token`      | Line Notifyトークンを入力する |
| `dc_notify_url`    | DiscordウェブフックURLを入力する |
| `slack_notify_url`    | SlackウェブフックURLを入力する |
| `teleg_token`    | Telegram APIトークンを入力する |
| `teleg_id`    | Telegram ChatIDを入力する |
| `b_timezone`    | お住いのタイムゾーンを指定する |
| `bNotify`    | 通知先を指定する |
| `bNotify_st`    | 通知基準を設定する |
| `nextepoch_leader_date`    | #次エポックスケジュール日時の通知有無 |


### **サービスファイルを設定する**
=== "ブロックプロデューサーノード"
    ```bash
    cat > $NODE_HOME/service/cnode-blocknotify.service << EOF 
    # file: /etc/systemd/system/cnode-blocknotify.service

    [Unit]
    Description=Cardano Node - SPO Blocknotify
    BindsTo=cnode-cncli-sync.service
    After=cnode-cncli-sync.service

    [Service]
    Type=simple
    RemainAfterExit=yes
    Restart=on-failure
    RestartSec=20
    User=$(whoami)
    WorkingDirectory=${NODE_HOME}/scripts
    Environment="NODE_HOME=${NODE_HOME}"
    ExecStart=/bin/bash -c 'cd ${NODE_HOME}/scripts/block-notify/ && python3 -u ./block_notify.py'
    StandardInput=tty-force
    SuccessExitStatus=143
    StandardOutput=syslog
    StandardError=syslog
    SyslogIdentifier=cnode-blocknotify
    TimeoutStopSec=5
    KillMode=mixed

    [Install]
    WantedBy=cnode-cncli-sync.service
    EOF
    ```

    ```
    sudo cp $NODE_HOME/service/cnode-blocknotify.service /etc/systemd/system/cnode-blocknotify.service
    ```

    ```
    sudo chmod 644 /etc/systemd/system/cnode-blocknotify.service
    sudo systemctl daemon-reload
    sudo systemctl enable cnode-blocknotify.service
    ```
    SPO BlockNotifyを起動する
    ```
    sudo systemctl start cnode-blocknotify.service
    ```

    環境変数にログ確認用エイリアスを追加する
    ```
    echo alias blocknotify='"journalctl --no-hostname -u cnode-blocknotify -f"' >> $HOME/.bashrc
    ```
    環境変数再読み込み
    ```
    source $HOME/.bashrc
    ```

    起動確認
    ```
    blocknotify
    ```
    以下の表示なら正常です。
    > [xxx] ブロック生成ステータス通知を起動しました  

</details>