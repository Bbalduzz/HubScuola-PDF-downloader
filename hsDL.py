import io
import json
import shutil
import requests
import sqlite3
import zipfile
import fitz

toc= []
def merge_pdf(extracted_files, output):
    pdffile = fitz.Document()
    n = 0
    for pdf in extracted_files:
        with open(output, 'wb') as handler:
            handler.write(pdf)
        pdffile.insert_pdf(fitz.open(stream=pdf, filetype="pdf"))
        n = n+1

    pdffile.set_toc(toc)
    pdffile.save(output)

class HubYoungDL:
    def __init__(self):
        self.session = requests.Session()
        self.login()

    def login(self):
        with open('cookies.txt', 'r') as f:
            datas = json.loads(f.read())
            login_data = {
                "username": datas["data"]['profile']["username"],
                "jwt": datas["data"]["hubEncryptedUser"],
                "sessionId": datas["data"]["sessionId"],
            }
        internal_login = self.session.post("https://ms-api.hubscuola.it/user/internalLogin", json=login_data).json()
        self.token = internal_login["tokenId"]
        self.session.headers["token-session"] = self.token

    def get_book_info(self, ID):
        lib = self.session.get("https://ms-api.hubscuola.it/getLibrary/young").json()
        for book in lib:
        	if book['id'] == int(ID):
        		return {
        			'title': book['title'],
        			'sub': book['subtitle'],
        			'authors': book['author'],
        			'editor': book['editor'],
        		}

    def gen_toc(self, chapter, pages_id):
	    sub_chap = chapter['children']
	    for i,sub in enumerate(sub_chap):
	        page_id = sub['children']
	        page_n = [pages_id.index(i)+1 for i in page_id]
	        toc.append([1, sub['title'], page_n[0]])

    def download_book(self, book_id, output_name):  # credits to @vvettoretti the sql snippet
        publication = self.session.get(f"https://ms-mms.hubscuola.it/downloadPackage/{book_id}/publication.zip?tokenId={self.token}")
        with zipfile.ZipFile(io.BytesIO(publication.content)) as archive:  # Sqlite cannot open db file from bytes stream
            archive.extract("publication/publication.db")
        db = sqlite3.connect("publication/publication.db")
        cursor = db.cursor()
        query = cursor.execute("SELECT offline_value FROM offline_tbl WHERE offline_path=?", ("meyoung/publication/" + book_id,)).fetchone()
        shutil.rmtree("./publication")

        pages = []
        for chapter in json.loads(query[0])['indexContents']['chapters']:
            url = f"https://ms-mms.hubscuola.it/public/{book_id}/{chapter['chapterId']}.zip?tokenId={self.token}&app=v2"
            self.gen_toc(chapter, json.loads(query[0])['pagesId'])
            documents = self.session.get(url)
            with zipfile.ZipFile(io.BytesIO(documents.content)) as archive:
                for file in sorted(archive.namelist()):
                    if ".pdf" in file:
                        with archive.open(file) as f:
                            pages.append(f.read())
        merge_pdf(pages, output_name)

if __name__ == '__main__':
	url = input('Enter book URL:\n')
	book_id = url.split('?')[0].removeprefix('https://young.hubscuola.it/viewer/')
	dl = HubYoungDL()
	book = dl.get_book_info(book_id)
	print(f'''
	[+] Book Found:
		- title: {book['title']}
		- subtitle: {book['sub']}
		- authors: {book['authors']}
		- editor: {book['editor']}
	''')
	dl.download_book(book_id, f"{book['title']}.pdf")



