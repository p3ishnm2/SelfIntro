import os
from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from werkzeug import secure_filename
import pymysql.cursors
import json
from watson_developer_cloud import VisualRecognitionV3
import requests

UPLOAD_FOLDER = 'static/images/'
ALLOWED_EXTENSIONS = set(
    ['PNG', 'JPG', 'JPEG', 'GIF', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)

# APIの設定
visual_recognition = VisualRecognitionV3(
    # The release date of the version of the API you want to use.
    '2018-03-19',
    iam_apikey='your_apikey')


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# 画像解析


def analyze(fname):
    with open(fname, 'rb') as images_file:
        classes = visual_recognition.classify(
            images_file,
            threshold='0.4',
            classifier_ids=["DefaultCustomModel_49867514"]).get_result()
        # unicodeで返ってくるので、utf-8に変換する。
        result = json.dumps(classes, indent=2).encode(
            'utf-8').decode('unicode_escape')
        # jsonを辞書型&リスト型にする
        result = json.loads(result)
        # 認識結果のclass=認識・特定した物体の名前だけを抽出する。
        score = result['images'][0]['classifiers'][0]['classes'][0]['score']
        score = score * 100
        result = result['images'][0]['classifiers'][0]['classes'][0]['class']
    return result, score

# データベースを検索


def selectsql(name):
    # データベースに接続
    connection = pymysql.connect(host='localhost',
                                 user='pi',
                                 password='raspberry',
                                 db='pi',
                                 charset='utf8',
                                 # Selectの結果をdictionary形式で受け取る
                                 cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        sql = "SELECT * FROM vegetable WHERE class=%s"
        cursor.execute(sql, name)
        # 必要なカラムの内容だけ抽出
        dbdata = cursor.fetchall()
        desc = dbdata[0]['description']
        connection.close()
    return desc

# メインルーチン


@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            img = UPLOAD_FOLDER + filename
            result = analyze(img)
            desc = selectsql(result[0])
            #audiofile = talk(result[0], desc)
            # 変更
            return render_template('index.html', img=img, score=result[1], message=result[0], desc=desc)
    return '''
    <!doctype html>
    <head>
    <meta charset="utf-8">
    <meta http-equiv=“X-UA-Compatible” content=“IE=edge”>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="http://code.jquery.com/jquery-1.11.1.min.js"></script>
    <link href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
    </head>
    <title>自己商品紹介</title>
    <h1>自己商品紹介</h1>
    <hr noshade>
    <h3>Upload & Analyze new File</h3>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file><input type=submit value=Upload></p>
    </form>
    '''


# @app.route('/<filename>')
# def uploaded_file(filename):
#    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
