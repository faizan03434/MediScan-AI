@echo off
echo Installing MediScan AI dependencies...
call "d:\Medical Mobile APP\ai-server\.venv\Scripts\activate.bat"
pip install numpy==1.26.4 opencv-python-headless==4.10.0.84 ultralytics==8.3.0 timm==1.0.11 scikit-learn==1.5.2
echo.
echo Verifying installs...
python -c "import numpy; print('numpy', numpy.__version__)"
python -c "import cv2; print('cv2', cv2.__version__)"
python -c "import timm; print('timm', timm.__version__)"
echo Done!
pause
