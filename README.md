# Master thesis: Using deep learning to obtain multimodal representations
Guidelines that I will try to follow throughout the project:

## Steps to reproduce the virtual environment and run scripts from the project

1. Clone the repo.
2. Install poetry from: https://github.com/sdispater/poetry
3. Navigate to the project directory where the ```pyproject.toml``` is.
4. Run ```poetry install```. This will install all dependencies specified in the pyproject.toml file and it will create a virtual environment.

## Keeping the code clean and identically formatted

- Pre-commit hooks are installed and set up for the project to ensure having identically formated code no matter the machine that is used for developing. Immediately after installation make sure to run
```poetry run pre-commit install --install-hooks```. Then, before each commit the pre-commit hooks will be run. They will check whether the code is formated accordingly. If not, the commit will fail and
 the errors will be reported. The hooks which are run are ```black```, ```flake8``` and ```mypy```.

- For manually running the code formater: ```poetry run black src/```.
- For manually running the linter: ```poetry run flake8 src/```.
- For manually runnnig the static type checker: ```poetry run mypy src/```.

## Testing the code
For running all tests run ```poetry run pytest src/```. This will run all tests and report if there are falling tests.

## Folder structure
Python files that are in the top most level in the sources directory. Theese python files are treated as scripts. All other python files that are
further down in the sources directory should be packed as packages and imported in the scripts as modules. An example is presented below.

```
models/
notebooks/
src/
 |
  -- script1.py
  -- script2.py
  -- package1/
        |
         -- module1.py
         -- module2.py
  -- package2/
        |
         -- module3.py
```

## Docstrings and static typing
An improved readability of the code will be achieved if with docstrings. On the other hand, using static typing helps more than just improving readability and provides usefull warning 
messages if something seems off. One option to use is the Google docstring format and the typing library included by default in python. An example is presented below.

```
from typing import List, Dict

def function(arg1: List[int], arg2: str) -> Dict[str, int]:
    """Summary line of the function.
    
    Extended description of the function if needed.
    
    Args:
        arg1: Description of the first input argument.
        arg2: Description of the second input argument.

    Returns:
        What the function returns

    """
    start_of_code += 1
    return_dict = {"some_var": start_of_code}

    return return_dict
```
Furthermore the typing library supports all kind of types such as ```Dict```, ```Tuple```, ```Set```, ```Union``` and so on.

## Logging vs printing

The only situation where ```print("Something")``` is allowed is in the top level python files. Otherwise, logging should be always used. The logging is included in the default
python library. The logging package has a lot of useful features:

 - Easy to see where and when (even what line no.) a logging call is being made from.
 - You can log to files, sockets, pretty much anything, all at the same time.
 - You can differentiate your logging based on severity.
 - Print doesn't have any of these.

[Stackoverlow](https://stackoverflow.com/questions/6918493/in-python-why-use-logging-instead-of-print) source
about printing vs logging.


## Notebooks

All notebooks are in the ```notebooks/``` directory and should be excluded from version control.

## Models

All saved models are in the ```models/``` directory and should be excluded from version control.

## Data

All datasets are in the ```data/``` directory and should be excluded from version control.

## Hyperparameters

All hyperparameters used to reproduce an experiment should be in the ```hyperparameters/``` directory. 


	
