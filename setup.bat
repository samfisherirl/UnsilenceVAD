CALL venv\Scripts\activate 

venv\Scripts\pyinstaller --windowed --add-data="C:\Users\dower\Documents\unsilence\dist\venv\Lib\site-packages\sv_ttk;sv_ttk" --icon=app.ico --noconfirm --clean unsilencer.py
