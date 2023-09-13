import requests
import fitz
import sys

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
    def __init__(self, pdf_bytes):
        self.pdf_bytes = pdf_bytes
        self.pdf = None
        self.load_pdf()

    def load_pdf(self):
        self.pdf = fitz.Document(stream=self.pdf_bytes, filetype="pdf")

    def save(self, filename):
        self.pdf.save(filename)


if __name__ == "__main__":
    book_url = input('[+] Enter book url:\n')
    book_id = book_url.split('?')[0].removeprefix('https://young.hubscuola.it/viewer/')
    hub = HubScuola(*CREDS)
    bookinfo = hub.getbookinfo(bookid)
    print(f'''[>] Book Found: 
  - title: {bookinfo['title']}
  - isbn: {bookinfo['isbn']}
''')
    auth = hub.getauth(bookinfo["jwt"], bookid)
    pdf_bytes = hub.downloadpdf(auth["token"], bookid, auth["layerHandle"])
    pdf_manager = PDFManager(pdf_bytes)
    pdf_manager.save("book.pdf")
