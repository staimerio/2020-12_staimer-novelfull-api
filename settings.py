# Retic
from retic import App as app

"""Set environment file path"""
app.env.read_env('.env.development', override=True)
