A simple example of how to create a package that executes a global command like 
```
uvicorn run main:app --reload
```

Instructions on how to run:
1. Create a virtual environment and activate it (these are instructions for Unix):
```
$ python -m venv virtualenv
$ source virtualenv/bin/activate
```
2. Starting from the root directory (`python_shebang/`), navigate into `package/` directory.
```
cd package/
```
3. install package into the virtual environment:
```
pip install -e .
```
3. install package into the virtual environment:
```
pip install -e .
```
3. install package into the virtual environment:
```
pip install -e .
```
3. install package into the virtual environment:
```
pip install -e .
```
3. install package into the virtual environment:
```
pip install -e .
```
4. run the command:
```
anacostia --reload
```
5. make a change to `anacostia/app.py` to see the automatic reload in action. 