INVENV=`python -c 'import sys; print sys.real_prefix' 2>/dev/null && INVENV=1 || INVENV=0`
if [ -z "$INVENV" ]; then
    echo "no virtual env"
else
    echo "deactivating virtual environment"
    deactivate
fi
if [ ! -f "venv" ]; then
    virtualenv venv
fi
echo "activating virtual env"
source venv/bin/activate
pip install --editable .
