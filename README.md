# 自分で写真を撮って、知ることで、一人でも展示会や動物園を楽しめるシステムの実装（その1）

自己商品（作品）紹介システムをハードウェアとして実装する 

## 背景（最初は真面目だった。）

商品説明の最終目的は「商品が売れること」である。そこで、商品を売るために必要となる適切な商品説明を、人手を介さずに行うために、商品自らが自分自身をセールストークするシステムを構築することを目的とする。

#### このシステムは、博物館の展示品や動物園の動物たちの説明にも応用できます。

1. 一人でそういったスポットには行きにくい
2. 知りたい・尋ねたいことがあっても、スタッフには話しかけにくい

そんな時にも役に立ちますし、逆に説明文から動物などの名前を当てるクイズにしてもいいかもしれませんね。

## これまでの記事の内容を組合わせる

- [IBM WatsonのVisual Recognitionで画像認識のカスタムモデルを作成する](https://qiita.com/p3ishnm2/items/dbb11403ba3ee9b84a6f)
- [IBM WatsonのVisual RecognitionをPythonで叩いて、Raspberry Piで画像認識カメラを自作する](https://qiita.com/p3ishnm2/items/c470866369bf5e3c1e81)
- [Raspberry PiをSQLサーバーにして、Python3からMySQLのデータを検索して表示させるまで](https://qiita.com/p3ishnm2/items/078d8d7a47ee3b7abc31)
- [Pythonでdocomoの音声合成APIを利用する](https://qiita.com/p3ishnm2/items/618d112babaa9cc3395d)

これらをもとに、

1. シャッターを押して写真を撮る
2. 画像解析APIに投げる
3. JSONが返ってくる
4. JSONから認識結果だけを抽出
5. 認識結果に対応した情報をデータベースから検索
6. 説明文を取得
7. 説明文を音声合成(docomoAPI)して音声ファイルに保存
8. ファイルが既存であればそこから再生。無ければもう一度音声合成

するようにプログラムを書いていきます。

```python
import RPi.GPIO as GPIO
from time import sleep, time
import json
from watson_developer_cloud import VisualRecognitionV3
from datetime import datetime
import subprocess
import pymysql.cursors
import os
import requests

# GPIOポートの設定 --- (*1)
LED_PORT = 4
PE_PORT = 18
SWITCH_PORT = 23

#GPIO.cleanup()

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PORT, GPIO.OUT)
GPIO.setup(PE_PORT, GPIO.OUT)
GPIO.setup(SWITCH_PORT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# APIの設定
visual_recognition = VisualRecognitionV3(
    #The release date of the version of the API you want to use.
    '2018-03-19',
    iam_apikey='apikey')

# データベースに接続
connection = pymysql.connect(host='hoge',
     user='hoge',
     password='hoge',
     db='hoge',
     charset='utf8',
     # Selectの結果をdictionary形式で受け取る
     cursorclass=pymysql.cursors.DictCursor)

# 写真の撮影コマンドを実行
def take_photo():
    now = datetime.now()
    fname = now.strftime('%Y-%m-%d_%H-%M-%S') + ".jpg"
    cmd = "fswebcam -r 1920x1080 " + fname
    #撮影コマンドを要求して、カメラを起動、撮影
    subprocess.check_output("fswebcam", shell=True)
    subprocess.check_output(cmd, shell=True)
    print("captured")
    # 画像認識
    with open(fname, 'rb') as images_file:
        classes = visual_recognition.classify(
        images_file,
        threshold='0.6',
        classifier_ids=["yourmodelID"]).get_result()
        #unicodeで返ってくるので、utf-8に変換する。
        result = json.dumps(classes, indent=2).encode('utf-8').decode('unicode_escape')
        #jsonを辞書型&リスト型にする
        result = json.loads(result)
        #認識結果のclass=認識・特定した物体の名前だけを抽出する。
        result = result['images'][0]['classifiers'][0]['classes'][0]['class']
    return result

# データベースを検索
def selectsql(name):
    with connection.cursor() as cursor:
        sql = "SELECT * FROM vegetable WHERE class=%s"
        cursor.execute(sql,name)
        #必要なカラムの内容だけ抽出 
        dbdata = cursor.fetchall()
        desc = dbdata[0]['description']
        return desc

#引数で指定した文字列を再生する
def talk(title, message, path="./"):

    if not os.path.isfile(path+title+".wav"): # 既に音声ファイルがあるかどうかを確認する
        url = 'https://api.apigw.smt.docomo.ne.jp/crayon/v1/textToSpeech?APIKEY='+'apikey2'

        params = {
              "Command":"AP_Synth",
              "SpeakerID":"1",
              "StyleID":"1",
              "SpeechRate":"1.15",
              "AudioFileFormat":"2",
              "TextData":message
            }

        r = requests.post(url, data=json.dumps(params))
        if r.status_code == requests.codes.ok:
            wav = r.content
            with open(path+title+".wav","wb") as fout:
                fout.write(wav)

    if os.path.isfile(path+title+".wav"): # APIでエラーが発生し、音声ファイルが生成されないときのため
        char = "aplay {}{}.wav".format(path, title)
        os.system(char)

# ブザーを鳴らす
def beep():
    pwm = GPIO.PWM(PE_PORT, 330)
    pwm.start(50)
    sleep(0.1)
    pwm.ChangeFrequency(440)
    sleep(0.1)
    pwm.stop()

#メインループ
try:
    sw = 0
    while True:
        if GPIO.input(SWITCH_PORT) == GPIO.HIGH:
        	# 押す、光る！鳴る！
            sw = 1
            GPIO.output(LED_PORT, GPIO.HIGH)
            beep()

            # 写真撮影
            result = take_photo()
            print(result)
            if result == '': continue

            #データベースにアクセス
            desc = selectsql(result)
            print(desc)

            # 喋らせよう
            talk(result, desc)

            if sw != 0: continue # 連続押し防止
            sw = 0
        else:
            sw = 0
            GPIO.output(LED_PORT, GPIO.LOW)
        sleep(0.1)

except KeyboardInterrupt:
    pass

GPIO.cleanup()

```

osもsubprocessもimportしている点や、カメラの起動後のオートフォーカスの時間を稼ぐために、1枚目のfswebcamの結果を破棄して、2枚目を解析するなど、冗長でうまくないところもありますが、ひとまず動いているので良しとします。

## 実行結果

```
$ python3 selfintro.py
captured
grape
軸が茶色いものは収穫してから日が経っています。また果皮に白っぽい粉が付着していますが、これは水分の蒸発を防ぐためのブルームというものです。この粉がまんべんなく付いているブドウは鮮度がよい証拠です。また、鮮度を保つ役割も持つため、食べる直前まで洗い流さないこと。なお、ブルームは食べても大丈夫ですよ。
再生中 WAVE ‘./grape.wav’ : Signed 16 bit Little Endian, レート 22050 Hz, モノラル
```

