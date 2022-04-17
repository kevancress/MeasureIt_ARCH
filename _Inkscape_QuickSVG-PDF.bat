@Echo off
setlocal ENABLEDELAYEDEXPANSION

:: EDIT VARIABLES HERE
set inkscapePath="D:\Additional Programs\Inkscape\inkscape\bin\inkscape.exe"
set outputType=pdf
set dpi=450


FOR /F "tokens=* USEBACKQ" %%g IN (`%inkscapePath% --version`) do (SET "inkscapeVersion=%%g")

echo This script converts .svg file to .pdf
echo Running with %inkscapeVersion%
echo.

set /a total=0
for %%i in (%*) do (
	set /a total=total+1
)
echo Conversion started. Will do %total% file(s).

echo.

set /a count=0

for %%i in (%*) do (

	set /a count=count+1

	if not exist "%%~di%%~piout" mkdir "%%~di%%~piout"

	echo %%i -^> "%%~di%%~piout\%%~ni.%outputType%" ^[!count!/%total%^]

	%inkscapePath% --batch-process --export-filename="%%~di%%~piout\%%~ni.%outputType%" --export-dpi=%dpi% %%i
) 

echo %count% file(s) converted from .svg to .pdf! (Saved in out folder)

:end
pause