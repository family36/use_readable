import requests
import json
import deepl
import pypdf
import time
import glob
import shutil
import os
from dotenv import load_dotenv

# 対象のPDFを分割
def split_pdf(target_pdf):
    reader = pypdf.PdfReader(f'pdf/{target_pdf}')
    for i, page in enumerate(reader.pages):
        writer = pypdf.PdfWriter()
        writer.add_page(page)
        writer.write(f'split/{i}.pdf')

# pdfを翻訳 
def translate_pdf():
    # DeepL初期設定
    load_dotenv()
    API_KEY = os.environ['API_KEY']
    translator = deepl.Translator(API_KEY)

    for i in range(len(glob.glob('split/*.pdf'))):
        # PDFを読み込む
        pdf_name = f'{i}.pdf'
        with open(f'split/{pdf_name}', 'rb') as f:
            page = f.read()

        try:
            # PDFをAPI送信
            files = {
                'file': (pdf_name, page, 'application/pdf')
            }
            query_url = 'https://api.readable.jp/toquery/'
            response = requests.post(query_url, files=files)

            # responseからurlとuuidを取得
            deepl_url = json.loads(response.text)['url']
            uuid = json.loads(response.text)['uuid']

            # urlからencoded_textを取得
            encoded_text = deepl_url.split('ja/')[1]

            # encoded_textをデコード
            text = requests.utils.unquote(encoded_text)

            # 翻訳
            result = translator.translate_text(text, source_lang='EN', target_lang='JA')
            result = str(result)

            # 翻訳結果をAPI送信
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
                'Content-Type': 'application/json',
                'Host': 'api.readable.jp',
                'Origin': 'https://readable.jp',
                'Referer': 'https://readable.jp/',
            }
            payload = {
                "body": result,
                "uuid": uuid,
                "original_filename": pdf_name
            }
            generate_url = 'https://api.readable.jp/generate/'
            response = requests.post(generate_url, headers=headers, json=payload)

            # responseからjaを取得
            ja_pdf_name = json.loads(response.text)['ja']
            jp_pdf_url = f'https://files.readable.jp/{ja_pdf_name}'

            # PDFをダウンロード
            response = requests.get(jp_pdf_url)
            with open(f'translated/{pdf_name}', 'wb') as f:
                f.write(response.content)

        except Exception as e:
            print(e)
            print(f'{pdf_name} is not translated.')
            time.sleep(3)
            continue

        print(f'{pdf_name} is translated.')
        time.sleep(3)

# translated内のpdfファイルを結合
def merge_pdf(merged_pdf_name):
    pdfs = glob.glob('translated/*.pdf')
    pdfs.sort()

    merger = pypdf.PdfMerger()
    for pdf in pdfs:
        merger.append(pdf)

    merger.write(merged_pdf_name)
    merger.close()

# splitとtranslated内のファイルを削除
def cleanup():
    shutil.rmtree('split')
    shutil.rmtree('translated')
    os.mkdir('split')
    os.mkdir('translated')

# splitとtranslatedディレクトリを作成
def create_dir():
    if not os.path.exists('split'):
        os.mkdir('split')
    if not os.path.exists('translated'):
        os.mkdir('translated')

if __name__ == '__main__':
    target_pdf = input('Please enter the name of the PDF file (e.g. sample.pdf): ')
    merged_pdf_name = f'{target_pdf.split(".")[0]}_translated.pdf'

    create_dir()
    cleanup()
    split_pdf(target_pdf)
    translate_pdf()
    merge_pdf(merged_pdf_name)
    cleanup()
    