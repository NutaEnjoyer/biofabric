from fastapi import HTTPException

def problem(status, title, detail, type_='about:blank', instance=None):
    raise HTTPException(status_code=status, detail={'type':type_,'title':title,'status':status,'detail':detail,'instance':instance})
