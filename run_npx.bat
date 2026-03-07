@echo off
echo Starting npx %* >> npx_log.txt
call npx.cmd %* 1>> npx_log.txt 2>&1
echo npx finished with error level %errorlevel% >> npx_log.txt
