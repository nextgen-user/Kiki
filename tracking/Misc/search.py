import requests
import bs4
import re
    
class Scraper():
    """
    Runs a basic search and returns the default answer provided by google.
    Google's default answers all have a class contaning BNeawe, s3v9rd, or
    orAP7Wnd, so we can just run a google query and parse the results
    example: google What is the Large Hadron Collider?
    """

    def __init__(self,query):
        self.search(query)
    
    def search(self, question):
        query = '+'.join(question.split(' '))
        url = f'https://www.google.com/search?q={query}&ie=utf-8&oe=utf-8'
        response = requests.get(url)
        soup = bs4.BeautifulSoup(response.text, 'html.parser')

        google_answers = soup.find_all("div", {"class": "BNeawe iBp4i AP7Wnd"})
        for answer in google_answers:
            if answer.text:
                return self.parse_result(answer.text)

        first_answers = soup.find_all("div", {"class": "BNeawe s3v9rd AP7Wnd"})
        for answer in first_answers:
            if answer.text:
                return self.parse_result(answer.text)

        all_div = soup.find_all("div")
        google_answer_keys = ['BNeawe', 's3v9rd', 'AP7Wnd', 'iBp4i']

        for div in all_div:
            for key in google_answer_keys:
                if key in div:
                    print("a")
                    return self.parse_result(div.text)

        # return 'No Answers Found'
    def parse_input(self, data):
        """This method gets the data and assigns it to an action"""
        data = data.lower()
        # say command is better if data has punctuation marks

        if "+"  in data and "%" in data:
            data = data.replace("?", "")
            data = data.replace("!", "")
            data = data.replace(",", "")
            regex_dot = re.compile('\\.(?!\\w)')
            # input sanitisation to not mess up urls / numbers
            self.data = regex_dot.sub("", data)

        elif "say" not in data:
            data = data.replace("?", "")
            data = data.replace("!", "")
            data = data.replace(",", "")
            data = data.replace(".", " ")
            regex_dot = re.compile('\\.(?!\\w)')
            # input sanitisation to not mess up urls / numbers
            self.data = regex_dot.sub("", data)
            

    def parse_result(self, result):
        result = result.split('\n')[0]
        if result.endswith('Wikipedia'):
            result = result[:result.find('Wikipedia')]
        result += '\n'
        
        return self.parse_input(result)

    def __call__(self):
        return self.data
