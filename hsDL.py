import requests
import fitz
import sys
import json

CREDS = ("your_username", "your_password")

class HubScuola:
    BASE_URL = "https://ms-api.hubscuola.it"
    PDF_URL = "https://ms-pdf.hubscuola.it"

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = ''
        self.login()

    def login(self):
        logindata = self.getlogindata()
        session = self.getsessiontoken(
            logindata["data"]["hubEncryptedUser"], 
            logindata["data"]["username"], 
            logindata["data"]["sessionId"]
        )
        self.token = session["tokenId"]

    def getlogindata(self):
        r = requests.get(
            "https://bce.mondadorieducation.it//app/mondadorieducation/login/loginJsonp", 
            params={"username": self.username, "password": self.password}
        )
        return r.json()

    def getsessiontoken(self, jwt, internalusername, sessionid):
        data = {"username": internalusername, "sessionId": sessionid, "jwt": jwt}
        r = requests.post(f"{self.BASE_URL}/user/internalLogin", json=data)
        return r.json()

    def getbookinfo(self, bookid):
        r = requests.get(
        	f"{self.BASE_URL}/meyoung/publication/{str(bookid)}", 
        	headers={"Token-Session": self.token}
        )
        return r.json()

    def getauth(self, jwt, bookid):
        r = requests.post(
            f"{self.PDF_URL}/i/d/{bookid}/auth", 
            json={"jwt": jwt, "origin": f"https://young.hubscuola.it/viewer/{bookid}?page=1"}, 
            headers={"PSPDFKit-Platform": "web", "PSPDFKit-Version": "protocol=3, client=2020.6.0, client-git=63c8a36705"}
        )
        return r.json()

    def downloadpdf(self, token, bookid, layerhandle):
        r = requests.get(
            f"{self.PDF_URL}/i/d/{bookid}/h/{layerhandle}/pdf?token={token}", 
            stream=True
        )
        total_size = int(r.headers.get('content-length', 0))
        downloaded = 0
        file = b""
        for data in r.iter_content(chunk_size=102400):
            downloaded += len(data)
            percentage = 100.0 * downloaded / total_size
            self._display_progress_bar(percentage)
            file += data
        return file

    @staticmethod
    def _display_progress_bar(percentage):
        bar_length = 50
        block = int(round(bar_length * percentage / 100))   
        progress = "|" + "=" * block + "-" * (bar_length - block) + "|"
        sys.stdout.write(f"\r{progress} {percentage:.2f}%")
        sys.stdout.flush()


class PDFManager:
    def __init__(self, pdf_bytes, bookchapters):
        self.pdf_bytes = pdf_bytes
        self.pdf = None
        self.load_pdf()
        self.toc = self.build_toc(bookchapters)

    def load_pdf(self):
        self.pdf = fitz.open(self.pdf_bytes, filetype="pdf")

    def save(self, filename):
        self.pdf.set_toc(self.toc)
        self.pdf.save(filename)

    def process_children(self, children, bookinfo, current_level, pagecount):
        toc_entries = []
        for child in children:
            if isinstance(child, int):
                if child in bookinfo["pagesId"]:
                    pagecount += 1
            else:
                title = child["title"]
                if len(children) > 1:
                    toc_entries.append([current_level, title, pagecount])
                pagecount = self.process_grandchildren(child["children"], bookinfo, pagecount)
        return toc_entries, pagecount

    def process_grandchildren(self, grandchildren, bookinfo, pagecount):
        for grandchild in grandchildren:
    	    if grandchild in bookinfo["pagesId"]:
                pagecount += 1
        return pagecount

    def build_toc(self, bookchapters):
        toc = []
        pagecount = 1
        CHAPTER_LEVEL = 1
        SUBCHAPTER_LEVEL = 2

        for chapter in bookchapters:
            toc.append([CHAPTER_LEVEL, chapter["title"], pagecount])
            toc_entries, pagecount = self.process_children(chapter["children"], bookinfo, SUBCHAPTER_LEVEL, pagecount)
            toc.extend(toc_entries)

        return toc

if __name__ == "__main__":
    book_url = input('Enter book URL:\n')
    bookid = book_url.split('?')[0].removeprefix('https://young.hubscuola.it/viewer/')
    hub = HubScuola(*CREDS)
    bookinfo = hub.getbookinfo(bookid)
    print(f'''[>] Book Found: 
	- title: {bookinfo['title']}
	- isbn: {bookinfo['isbn']}
''')
    auth = hub.getauth(bookinfo["jwt"], bookid)
    pdf_bytes = hub.downloadpdf(auth["token"], bookid, auth["layerHandle"])
    pdf_manager = PDFManager(pdf_bytes, bookinfo["indexContents"]["chapters"])
    pdf_manager.save(f"{bookinfo['title']}.pdf")
