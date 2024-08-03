@echo off
:Begin
echo %time%
echo "start"
z:/Enviroments/ml/Scripts/python.exe z:/GG/Source/jamming_bot/jamming_bot.py
echo "done"
echo %time%
echo sleep 600 sec
timeout 600 > NUL
goto begin