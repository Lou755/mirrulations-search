# Sets the PWD to the src directory and starts the gunicorn server on port 80 using the configuration in conf/gunicorn.py.
export PYTHONPATH="$PWD/src"
exec gunicorn -c conf/gunicorn.py mirrsearch.app:app --bind 0.0.0.0:80

