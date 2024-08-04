@echo off
:Begin
set COLOREDLOGS_LEVEL_STYLES='spam=22;debug=28;verbose=34;notice=220;warning=202;success=118,bold;error=124;critical=background=red'
echo %time%
echo "start"
z:/Enviroments/ml/Scripts/python.exe z:/GG/Source/jamming_bot/jamming_bot.py
echo "done"
echo %time%
echo sleep 600 sec
timeout 600 > NUL
goto begin