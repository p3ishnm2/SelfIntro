# 自分で写真を撮って説明を聞くことで、お一人様でも展示会や動物園を楽しめるシステム（その2 | Webアプリ化）

#[前回](https://qiita.com/p3ishnm2/items/09af10487f6871a2e620)のあらすじ

上の記事の通り、前回は商品や作品が自己紹介してくれるシステムを作りました。このシステムはRaspberry Piに接続したカメラで撮影し、解析した結果をもとに対応する説明文を音声出力して、自己紹介してくれます。

![IMG_4733](/Users/yoshimatsushunpei/Desktop/高専卒研/IMG_4733.jpg)

# Webアプリ化

今回はflaskでシステムをWebアプリ化していきます。ファイル構成は以下の通り

```
selfintro
├── templates
│   ├── index.html
│   └── layout.html
└── uploads.py
```

uploads.pyで最初のページを表示し、画像がアップロードされたのに合わせて、解析結果と説明文をindex.htmlに受け渡します。

uploads.pyでは、[公式docs](http://flask.pocoo.org/docs/1.0/patterns/fileuploads/)とこの辺の記事を参考にしました。

[<Flask> Uploading - ねこゆきのメモ](http://nekoyukimmm.hatenablog.com/entry/2016/05/27/162736)

[Flaskで画像アップローダー - Qiita](https://qiita.com/Gen6/items/f1636be0fe479f42b3ee)

### プログラム

```python
import os
from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from werkzeug import secure_filename
import pymysql.cursors
import json
from watson_developer_cloud import VisualRecognitionV3

UPLOAD_FOLDER = './'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)

# APIの設定
visual_recognition = VisualRecognitionV3(
    #The release date of the version of the API you want to use.
    '2018-03-19',
    iam_apikey='R3gEt5Rp_ZxhxpsO60pL4ipb97WYEGHtU_a8LmDB0Rbo')

# データベースに接続
connection = pymysql.connect(host='localhost',
     user='pi',
     password='raspberry',
     db='pi',
     charset='utf8',
     # Selectの結果をdictionary形式で受け取る
     cursorclass=pymysql.cursors.DictCursor)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

#画像解析
def analyze(fname):
    with open(fname, 'rb') as images_file:
        classes = visual_recognition.classify(
        images_file,
        threshold='0.6',
        classifier_ids=["DefaultCustomModel_49867514"]).get_result()
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

#画像アップロード
@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            #画像解析
            result = analyze(filename)
            #データベースにアクセス
            desc = selectsql(result)
            return render_template('index.html', message=result, desc=desc) 
    #最初のページはここに作っちゃいます
    return '''
    <!doctype html>
    <title>自己商品紹介システム</title>
    <h1>自己商品紹介システム</h1>
    <h2>Upload & Analyze new File</h2>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

#おまじない
if __name__ == '__main__':
    app.run(debug=True, port=8000)

```

```html
{% extends "layout.html" %}
{% block content %}
<title>自己商品紹介</title>
<h1>自己商品紹介</h1>
<h2>Upload & Analyze new File</h2>
<form action="" method=post enctype=multipart/form-data>
  <p><input type=file name=file>
     <input type=submit value=Upload>
</form>
{% if message %}
<p>識別できました。</p>
<p>{{ message }}</p>
{% endif %}
{% if desc %}
<p>{{ desc }}</p>
{% endif %}
{% endblock %}
```

続いて、index.htmlのテンプレートを作成

```
<!doctype html>
<html>
<head>
<body>
{% block content %}
<!-- ここにメインコンテンツを書く -->
{% endblock %}
</body>
</head>
```

# 動作確認

![IMG_4734](/Users/yoshimatsushunpei/Downloads/IMG_4734.gif)

アップした商品の画像を予め機械学習したカスタムモデルが判別して、その結果に合わせてデータベースから商品や作品の説明を表示してくれるのが確認できます。
これで、最低限の機能は実装出来ました。今はラズパイをWebサーバにしているので、クラウド上にでもサーバー立てて公開するところまで持っていきたい。