from fastapi import FastAPI




app=FastAPI(title="TutorDesk")


@app.get('/')
def health():
    return  {"message": "TutorDesk API is running"}