A simple python file to prepare audio files (wavs and mp3s) for training , notably in Ace-Step 2 .

**It is provided as-is and the user takes responsibility for due dilgence as to its usage
**


**What will it do ?**

**NB use a copy of the audio files that you want processed in case it goes tits up**


1.It uses tkinter, so instead of living in the 17th century and using an obscenely long command line, it will open a requestor - you select the folder of audio files that you wish to process

2.It will then rename the files within that folder to their tags like this example : '1.Things That Dreams Are Made Of' -> 'Human League - Things That Dreams Are Made Of'

3.A new folder is made in the same folder as the requested one but with '_processed' appended to the folder name

4.The audio file is then converted to a 48kHz wav file and save in the new processed folder

5.The filename is then looked up in Genius.com and gets the lyrics to the audio file , saving them as (audio filename).txt . This is the format that Ace-Step2 uses in its trainer

6.The program cycle through each audio file

7.Go through the txt files and check the filesizes , they should only be 1-2kb at most. 

8.The python code will also recheck Genius but removing any additional artist that has this format 'Johnny Cash,Chris Beach - Hurt' , it will recheck for 'Johnny Cash - Hurt'

9.The python code will recheck for a third and final time if there is bracketed text in the filename (eg a remix name) , 'Abba - Voulez Vous (star remix)' , it will recheck for 'Abba - Voulex Vous'


The renaming and the rechecks give the best chance of returning the correct lyrics - **it is not infallible **



What do you need to do ?

1. ffmpeg installed to your system with Path added to env variables

2. Obtain a Genius api access token and save it in the python file at line 32 (inside the inverted commas)

<img width="417" height="60" alt="image" src="https://github.com/user-attachments/assets/5002fae0-72ad-4f64-b574-8d790d4bf3ea" />



**Installation **

Personally I make a small venv (about 20mb) to run it, to keep it seperate

**Making a Venv in a cmd window**

Python.exe -m venv venv

venv\Scripts\activate.bat

**Requirements ie pip install them in**

**Python <13.0**

requests

bs4

pydub

music-tag



**python >=13.0**

audioop-lts

requests

bs4

pydub
music-tag
