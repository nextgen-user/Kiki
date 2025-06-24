import yagmail
content = "Hi!"
yag = yagmail.SMTP('vaibhavarduino@gmail.com', 'bigxeizelixaoina')
contents = [content, '🤖 Sent from Kiki 🤖']
yag.send(['vaibhavarduino@gmail.com'], 'Hello Mom', contents)